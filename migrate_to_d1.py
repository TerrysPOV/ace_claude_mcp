#!/usr/bin/env python3
"""
ACE Migration Tool - Migrate local playbooks to D1 database.

This script reads existing local playbook files and generates SQL INSERT
statements for migrating to Cloudflare D1, or can call the D1 API directly.

Usage:
    # Generate SQL file
    python migrate_to_d1.py --output migration.sql

    # Execute directly via wrangler (requires wrangler CLI)
    python migrate_to_d1.py --execute --database ace-playbook

    # Migrate specific project only
    python migrate_to_d1.py --project finance --output finance_migration.sql
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration - matches ace_core.py
ACE_DIR = Path.home() / ".ace"
PLAYBOOKS_DIR = ACE_DIR / "playbooks"
REFLECTIONS_DIR = ACE_DIR / "reflections"
PROJECTS_FILE = ACE_DIR / "projects.json"

# Legacy single-file locations (v1)
LEGACY_PLAYBOOK = ACE_DIR / "playbook.md"
LEGACY_REFLECTIONS = ACE_DIR / "reflections.jsonl"


def parse_entry(line: str) -> dict | None:
    """Parse a playbook entry line into components."""
    # Support format with optional project marker
    pattern = r"\[([a-z]{3}-\d{5})\]\s+helpful=(\d+)\s+harmful=(\d+)(?:\s+\[([^\]]+)\])?\s+::\s+(.+)"
    match = re.match(pattern, line.strip())
    if match:
        return {
            "id": match.group(1),
            "helpful": int(match.group(2)),
            "harmful": int(match.group(3)),
            "project_id": match.group(4),
            "content": match.group(5),
        }
    # Try old format without project marker
    old_pattern = r"\[([a-z]{3}-\d{5})\]\s+helpful=(\d+)\s+harmful=(\d+)\s+::\s+(.+)"
    match = re.match(old_pattern, line.strip())
    if match:
        return {
            "id": match.group(1),
            "helpful": int(match.group(2)),
            "harmful": int(match.group(3)),
            "project_id": None,
            "content": match.group(4),
        }
    return None


def get_current_section(lines: list[str], line_idx: int) -> str | None:
    """Find the section header for a given line index."""
    sections = [
        "STRATEGIES & INSIGHTS",
        "FORMULAS & CALCULATIONS",
        "COMMON MISTAKES TO AVOID",
        "DOMAIN KNOWLEDGE",
    ]
    for i in range(line_idx, -1, -1):
        for section in sections:
            if lines[i].strip() == f"## {section}":
                return section
    return None


def escape_sql(s: str) -> str:
    """Escape string for SQL."""
    return s.replace("'", "''")


def migrate_playbook(playbook_path: Path, project_id: str, user_id: str) -> list[str]:
    """Generate SQL INSERT statements for a playbook file."""
    if not playbook_path.exists():
        return []

    content = playbook_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    statements = []

    for i, line in enumerate(lines):
        entry = parse_entry(line)
        if entry:
            section = get_current_section(lines, i)
            if section:
                # Use entry's project_id if present, otherwise use the file's project
                entry_project = entry["project_id"] or project_id
                statements.append(
                    "INSERT OR IGNORE INTO entries "
                    "(entry_id, project_id, user_id, section, content, helpful_count, harmful_count) "
                    f"VALUES ('{entry['id']}', '{escape_sql(entry_project)}', '{escape_sql(user_id)}', "
                    f"'{escape_sql(section)}', '{escape_sql(entry['content'])}', {entry['helpful']}, {entry['harmful']});"
                )

    return statements


def migrate_reflections(reflections_path: Path, project_id: str, user_id: str) -> list[str]:
    """Generate SQL INSERT statements for a reflections file."""
    if not reflections_path.exists():
        return []

    statements = []
    with open(reflections_path, encoding="utf-8") as f:
        for line in f:
            try:
                reflection = json.loads(line.strip())
                task_summary = escape_sql(reflection.get("task_summary", ""))
                outcome = escape_sql(reflection.get("outcome", "unknown"))
                learnings = escape_sql(json.dumps(reflection.get("learnings", [])))
                timestamp = reflection.get("timestamp", datetime.now().isoformat())

                statements.append(
                    "INSERT INTO reflections (project_id, user_id, task_summary, outcome, learnings, created_at) "
                    f"VALUES ('{escape_sql(project_id)}', '{escape_sql(user_id)}', '{task_summary}', "
                    f"'{outcome}', '{learnings}', '{timestamp}');"
                )
            except json.JSONDecodeError:
                continue

    return statements


def migrate_projects(user_id: str) -> list[str]:
    """Generate SQL INSERT statements for projects."""
    statements = []

    # Always ensure global project exists
    statements.append(
        "INSERT OR IGNORE INTO projects (project_id, user_id, description) "
        f"VALUES ('global', '{escape_sql(user_id)}', 'Universal patterns and insights shared across all projects');"
    )

    # Load projects from file if exists
    if PROJECTS_FILE.exists():
        projects = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
        for proj_id, meta in projects.items():
            if proj_id != "global":
                desc = escape_sql(meta.get("description", ""))
                statements.append(
                    "INSERT OR IGNORE INTO projects (project_id, user_id, description) "
                    f"VALUES ('{escape_sql(proj_id)}', '{escape_sql(user_id)}', '{desc}');"
                )

    return statements


def discover_playbooks() -> dict[str, Path]:
    """Discover all playbook files (both legacy and multi-project)."""
    playbooks = {}

    # Check for legacy single-file playbook (v1)
    if LEGACY_PLAYBOOK.exists():
        playbooks["global"] = LEGACY_PLAYBOOK

    # Check for multi-project playbooks (v2)
    if PLAYBOOKS_DIR.exists():
        for playbook_file in PLAYBOOKS_DIR.glob("*.md"):
            project_id = playbook_file.stem
            playbooks[project_id] = playbook_file

    return playbooks


def discover_reflections() -> dict[str, Path]:
    """Discover all reflection files."""
    reflections = {}

    # Check for legacy single-file reflections (v1)
    if LEGACY_REFLECTIONS.exists():
        reflections["global"] = LEGACY_REFLECTIONS

    # Check for multi-project reflections (v2)
    if REFLECTIONS_DIR.exists():
        for refl_file in REFLECTIONS_DIR.glob("*.jsonl"):
            project_id = refl_file.stem
            reflections[project_id] = refl_file

    return reflections


def generate_migration(project_filter: str | None = None, user_id: str = "default") -> str:
    """Generate full migration SQL."""
    lines = [
        "-- ACE Migration Script",
        f"-- Generated: {datetime.now().isoformat()}",
        "-- This script migrates local playbook data to D1",
        "",
        "-- Ensure schema exists (run schema.sql first if needed)",
        "",
    ]

    # Migrate projects
    lines.append("-- Projects")
    lines.extend(migrate_projects(user_id))
    lines.append("")

    # Discover and migrate playbooks
    playbooks = discover_playbooks()
    for project_id, playbook_path in playbooks.items():
        if project_filter and project_id != project_filter:
            continue
        lines.append(f"-- Playbook entries for project: {project_id}")
        statements = migrate_playbook(playbook_path, project_id, user_id)
        if statements:
            lines.extend(statements)
        else:
            lines.append(f"-- No entries found in {playbook_path}")
        lines.append("")

    # Discover and migrate reflections
    reflections = discover_reflections()
    for project_id, refl_path in reflections.items():
        if project_filter and project_id != project_filter:
            continue
        lines.append(f"-- Reflections for project: {project_id}")
        statements = migrate_reflections(refl_path, project_id, user_id)
        if statements:
            lines.extend(statements)
        else:
            lines.append(f"-- No reflections found in {refl_path}")
        lines.append("")

    return "\n".join(lines)


def execute_migration(database: str, sql: str) -> bool:
    """Execute migration via wrangler d1 execute."""
    try:
        # Write SQL to temp file
        temp_file = Path("/tmp/ace_migration.sql")
        temp_file.write_text(sql, encoding="utf-8")

        # Execute via wrangler
        result = subprocess.run(
            ["wrangler", "d1", "execute", database, "--file", str(temp_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error executing migration: {result.stderr}", file=sys.stderr)
            return False

        print(result.stdout)
        return True

    except FileNotFoundError:
        print("Error: wrangler CLI not found. Install with: npm install -g wrangler", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Migrate ACE playbooks from local files to D1 database"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output SQL file path (default: stdout)",
    )
    parser.add_argument(
        "--execute", "-x",
        action="store_true",
        help="Execute migration directly via wrangler",
    )
    parser.add_argument(
        "--database", "-d",
        default="ace-playbook",
        help="D1 database name (default: ace-playbook)",
    )
    parser.add_argument(
        "--project", "-p",
        help="Migrate specific project only",
    )
    parser.add_argument(
        "--user-id",
        default="default",
        help="User ID to associate with migrated data (default: default)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without doing anything",
    )

    args = parser.parse_args()

    # Check for local data
    playbooks = discover_playbooks()
    reflections = discover_reflections()

    if not playbooks and not reflections:
        print("No local ACE data found to migrate.", file=sys.stderr)
        print(f"Checked: {ACE_DIR}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("Found playbooks:")
        for proj, path in playbooks.items():
            print(f"  - {proj}: {path}")
        print("\nFound reflections:")
        for proj, path in reflections.items():
            print(f"  - {proj}: {path}")
        sys.exit(0)

    # Generate migration SQL
    sql = generate_migration(args.project, args.user_id)

    if args.execute:
        print(f"Executing migration to database: {args.database}")
        success = execute_migration(args.database, sql)
        sys.exit(0 if success else 1)
    elif args.output:
        Path(args.output).write_text(sql, encoding="utf-8")
        print(f"Migration SQL written to: {args.output}")
    else:
        print(sql)


if __name__ == "__main__":
    main()
