"""
ACE Core Logic - Pure functions without MCP dependencies.

This module contains all the business logic for the ACE playbook system,
separated from the MCP server for testability. Supports multi-project playbooks.
"""

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from typing import Optional

# Configuration
ACE_DIR = Path.home() / ".ace"
PLAYBOOKS_DIR = ACE_DIR / "playbooks"
REFLECTIONS_DIR = ACE_DIR / "reflections"
PROJECTS_FILE = ACE_DIR / "projects.json"

# Thread lock for file operations
_file_lock = threading.Lock()

# Section prefixes for ID generation
SECTION_PREFIXES = {
    "STRATEGIES & INSIGHTS": "str",
    "FORMULAS & CALCULATIONS": "cal",
    "COMMON MISTAKES TO AVOID": "mis",
    "DOMAIN KNOWLEDGE": "dom",
}

DEFAULT_PLAYBOOK = """## STRATEGIES & INSIGHTS
[str-00001] helpful=0 harmful=0 :: Break complex problems into smaller, manageable steps.
[str-00002] helpful=0 harmful=0 :: Validate assumptions before proceeding with solutions.

## FORMULAS & CALCULATIONS
[cal-00001] helpful=0 harmful=0 :: ROI = (Gain - Cost) / Cost * 100

## COMMON MISTAKES TO AVOID
[mis-00001] helpful=0 harmful=0 :: Don't assume input data is clean - always validate.

## DOMAIN KNOWLEDGE
[dom-00001] helpful=0 harmful=0 :: Context window limits require prioritizing relevant information.
"""


def _ensure_dirs():
    """Create ACE directories if they don't exist."""
    PLAYBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    REFLECTIONS_DIR.mkdir(parents=True, exist_ok=True)


def _get_playbook_path(project_id: str = "global") -> Path:
    """Get path to playbook file for a project."""
    return PLAYBOOKS_DIR / f"{project_id}.md"


def _get_reflections_path(project_id: str = "global") -> Path:
    """Get path to reflections file for a project."""
    return REFLECTIONS_DIR / f"{project_id}.jsonl"


def _ensure_playbook(project_id: str = "global"):
    """Create playbook with default content if it doesn't exist."""
    _ensure_dirs()
    playbook_path = _get_playbook_path(project_id)
    if not playbook_path.exists():
        if project_id == "global":
            playbook_path.write_text(DEFAULT_PLAYBOOK, encoding="utf-8")
        else:
            # Create empty playbook for non-global projects
            playbook_path.write_text(f"# Project: {project_id}\n\n", encoding="utf-8")


def _read_playbook_content(project_id: str = "global") -> str:
    """Read playbook content, creating default if needed."""
    _ensure_playbook(project_id)
    return _get_playbook_path(project_id).read_text(encoding="utf-8")


def _write_playbook_content(content: str, project_id: str = "global"):
    """Write content to playbook file."""
    _ensure_dirs()
    _get_playbook_path(project_id).write_text(content, encoding="utf-8")


def _parse_entry(line: str) -> dict | None:
    """Parse a playbook entry line into components."""
    # Support both old format and new format with project marker
    pattern = r"\[([a-z]{3}-\d{5})\]\s+helpful=(\d+)\s+harmful=(\d+)(?:\s+\[([^\]]+)\])?\s+::\s+(.+)"
    match = re.match(pattern, line.strip())
    if match:
        return {
            "id": match.group(1),
            "helpful": int(match.group(2)),
            "harmful": int(match.group(3)),
            "project_id": match.group(4),  # May be None
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


def _format_entry(entry_id: str, helpful: int, harmful: int, content: str, project_marker: str | None = None) -> str:
    """Format an entry as a playbook line."""
    if project_marker:
        return f"[{entry_id}] helpful={helpful} harmful={harmful} [{project_marker}] :: {content}"
    return f"[{entry_id}] helpful={helpful} harmful={harmful} :: {content}"


def _get_next_id(prefix: str, *project_ids: str) -> str:
    """Generate the next available ID across specified projects."""
    max_num = 0
    pattern = rf"\[{prefix}-(\d{{5}})\]"

    for project_id in project_ids:
        playbook_path = _get_playbook_path(project_id)
        if playbook_path.exists():
            content = playbook_path.read_text(encoding="utf-8")
            matches = re.findall(pattern, content)
            if matches:
                max_num = max(max_num, max(int(m) for m in matches))

    return f"{prefix}-{max_num + 1:05d}"


def _get_section_content(content: str, section: str) -> tuple[int, int, list[str]]:
    """Get section boundaries and lines. Returns (start_idx, end_idx, lines)."""
    lines = content.split("\n")
    section_header = f"## {section}"
    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        if line.strip() == section_header:
            start_idx = i
        elif start_idx is not None and line.strip().startswith("## "):
            end_idx = i
            break

    if start_idx is None:
        return -1, -1, []

    if end_idx is None:
        end_idx = len(lines)

    return start_idx, end_idx, lines[start_idx:end_idx]


def _similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _load_projects() -> dict:
    """Load projects metadata."""
    if PROJECTS_FILE.exists():
        return json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    return {"global": {"description": "Universal patterns and insights"}}


def _save_projects(projects: dict):
    """Save projects metadata."""
    _ensure_dirs()
    PROJECTS_FILE.write_text(json.dumps(projects, indent=2), encoding="utf-8")


def read_playbook(project_id: str = "global") -> str:
    """Return merged playbook content (global + project-specific)."""
    with _file_lock:
        # Always read global
        global_content = _read_playbook_content("global")

        if project_id == "global":
            return global_content

        # Read project-specific and merge
        project_content = _read_playbook_content(project_id)

        # Parse both into sections
        sections: dict[str, list[str]] = {}
        for section in SECTION_PREFIXES.keys():
            sections[section] = []

        # Add global entries first
        for line in global_content.split("\n"):
            entry = _parse_entry(line)
            if entry:
                section = None
                for s in SECTION_PREFIXES.keys():
                    _, _, section_lines = _get_section_content(global_content, s)
                    if line.strip() in [l.strip() for l in section_lines]:
                        section = s
                        break
                if section:
                    sections[section].append(line.strip())

        # Add project entries with marker
        for line in project_content.split("\n"):
            entry = _parse_entry(line)
            if entry:
                section = None
                for s in SECTION_PREFIXES.keys():
                    _, _, section_lines = _get_section_content(project_content, s)
                    if line.strip() in [l.strip() for l in section_lines]:
                        section = s
                        break
                if section:
                    # Add project marker if not already present
                    if f"[{project_id}]" not in line:
                        entry_line = _format_entry(
                            entry["id"], entry["helpful"], entry["harmful"],
                            entry["content"], project_id
                        )
                    else:
                        entry_line = line.strip()
                    sections[section].append(entry_line)

        # Format merged output
        output_lines = []
        for section in SECTION_PREFIXES.keys():
            if sections[section]:
                output_lines.append(f"## {section}")
                output_lines.extend(sections[section])
                output_lines.append("")

        return "\n".join(output_lines)


def get_section(section: str, project_id: str = "global") -> str:
    """Get all entries from a specific section of the playbook."""
    valid_sections = list(SECTION_PREFIXES.keys())
    if section not in valid_sections:
        return f"Invalid section. Must be one of: {valid_sections}"

    with _file_lock:
        merged = read_playbook(project_id)
        _, _, section_lines = _get_section_content(merged, section)

        if not section_lines:
            return f"Section '{section}' not found in playbook."

        return "\n".join(section_lines)


def add_entry(section: str, content: str, project_id: str = "global") -> str:
    """Add a new entry to the playbook with auto-generated ID and counters set to 0."""
    if section not in SECTION_PREFIXES:
        return f"Invalid section. Must be one of: {list(SECTION_PREFIXES.keys())}"

    prefix = SECTION_PREFIXES[section]

    with _file_lock:
        # Get next ID across all projects to avoid collisions
        all_projects = list(_load_projects().keys())
        new_id = _get_next_id(prefix, *all_projects)
        new_entry = _format_entry(new_id, 0, 0, content.strip())

        playbook_content = _read_playbook_content(project_id)
        start_idx, end_idx, section_lines = _get_section_content(playbook_content, section)

        if start_idx == -1:
            # Section doesn't exist, add it at the end
            playbook_content = playbook_content.rstrip() + f"\n\n## {section}\n{new_entry}\n"
        else:
            lines = playbook_content.split("\n")
            # Insert before the next section or at the end
            insert_idx = end_idx
            # Find last non-empty line in section
            for i in range(end_idx - 1, start_idx, -1):
                if lines[i].strip():
                    insert_idx = i + 1
                    break
            lines.insert(insert_idx, new_entry)
            playbook_content = "\n".join(lines)

        _write_playbook_content(playbook_content, project_id)
        return f"Added entry [{new_id}] to '{section}' (project: {project_id})"


def update_counters(entry_id: str, helpful_delta: int, harmful_delta: int) -> str:
    """Update the helpful/harmful counters for an entry."""
    pattern = rf"\[{re.escape(entry_id)}\]\s+helpful=(\d+)\s+harmful=(\d+)(?:\s+\[[^\]]+\])?\s+::\s+(.+)"

    with _file_lock:
        # Search across all project playbooks
        for playbook_file in PLAYBOOKS_DIR.glob("*.md"):
            project_id = playbook_file.stem
            content = playbook_file.read_text(encoding="utf-8")
            match = re.search(pattern, content)

            if match:
                old_helpful = int(match.group(1))
                old_harmful = int(match.group(2))
                entry_content = match.group(3)

                new_helpful = max(0, old_helpful + helpful_delta)
                new_harmful = max(0, old_harmful + harmful_delta)

                new_entry = _format_entry(entry_id, new_helpful, new_harmful, entry_content)
                new_content = re.sub(pattern, new_entry, content)

                _write_playbook_content(new_content, project_id)
                return f"Updated [{entry_id}]: helpful={old_helpful}->{new_helpful}, harmful={old_harmful}->{new_harmful}"

        return f"Entry '{entry_id}' not found in playbook."


def remove_entry(entry_id: str) -> str:
    """Remove an entry from the playbook by its ID."""
    pattern = rf"^\[{re.escape(entry_id)}\]\s+helpful=\d+\s+harmful=\d+(?:\s+\[[^\]]+\])?\s+::.*$"

    with _file_lock:
        # Search across all project playbooks
        for playbook_file in PLAYBOOKS_DIR.glob("*.md"):
            project_id = playbook_file.stem
            content = playbook_file.read_text(encoding="utf-8")
            lines = content.split("\n")
            new_lines = []
            found = False

            for line in lines:
                if re.match(pattern, line.strip()):
                    found = True
                else:
                    new_lines.append(line)

            if found:
                _write_playbook_content("\n".join(new_lines), project_id)
                return f"Removed entry [{entry_id}]"

        return f"Entry '{entry_id}' not found in playbook."


def log_reflection(task_summary: str, outcome: str, learnings: list[str], project_id: str = "global") -> str:
    """Log a task reflection for later curation into the playbook."""
    reflection = {
        "timestamp": datetime.now().isoformat(),
        "task_summary": task_summary,
        "outcome": outcome,
        "learnings": learnings,
    }

    with _file_lock:
        _ensure_dirs()
        reflections_path = _get_reflections_path(project_id)
        with open(reflections_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(reflection) + "\n")

    return f"Logged reflection with {len(learnings)} learning(s) for task: {task_summary[:50]}..."


def curate_playbook(project_id: Optional[str] = None, harmful_threshold: int = 3) -> str:
    """Curate the playbook by removing harmful entries and deduplicating."""
    with _file_lock:
        # Determine which projects to curate
        if project_id:
            projects = [project_id]
        else:
            projects = [f.stem for f in PLAYBOOKS_DIR.glob("*.md")]

        total_removed = []
        all_entries = []

        for proj in projects:
            playbook_path = _get_playbook_path(proj)
            if not playbook_path.exists():
                continue

            content = playbook_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            new_lines = []

            for line in lines:
                entry = _parse_entry(line)
                if entry:
                    if entry["harmful"] > entry["helpful"] + harmful_threshold:
                        total_removed.append(entry["id"])
                    else:
                        new_lines.append(line)
                        all_entries.append(entry)
                else:
                    new_lines.append(line)

            _write_playbook_content("\n".join(new_lines), proj)

        # Find duplicates across all remaining entries
        duplicates = []
        for i, e1 in enumerate(all_entries):
            for e2 in all_entries[i + 1:]:
                sim = _similarity(e1["content"], e2["content"])
                if sim > 0.8:
                    duplicates.append((e1["id"], e2["id"], f"{sim:.0%}"))

        result = []
        if total_removed:
            result.append(f"Removed {len(total_removed)} harmful entries: {total_removed}")
        else:
            result.append("No harmful entries to remove.")

        if duplicates:
            dup_report = "; ".join([f"{d[0]} ~ {d[1]} ({d[2]})" for d in duplicates[:5]])
            result.append(f"Potential duplicates found: {dup_report}")
            if len(duplicates) > 5:
                result.append(f"  ...and {len(duplicates) - 5} more")
        else:
            result.append("No duplicate entries found.")

        return "\n".join(result)


def search_playbook(query: str, project_id: str = "global") -> str:
    """Search the playbook for entries containing the query keywords."""
    with _file_lock:
        merged = read_playbook(project_id)

    query_lower = query.lower()
    keywords = query_lower.split()
    matches = []

    for line in merged.split("\n"):
        entry = _parse_entry(line)
        if entry:
            content_lower = entry["content"].lower()
            if any(kw in content_lower for kw in keywords):
                matches.append(line.strip())

    if not matches:
        return f"No entries found matching '{query}'"

    return f"Found {len(matches)} matching entries:\n" + "\n".join(matches)


def list_projects() -> str:
    """List all projects in the playbook system."""
    with _file_lock:
        projects = _load_projects()
        lines = []
        for proj_id, meta in projects.items():
            desc = meta.get("description", "")
            lines.append(f"- {proj_id}{': ' + desc if desc else ''}")
        return "\n".join(lines) if lines else "No projects found."


def create_project(project_id: str, description: Optional[str] = None) -> str:
    """Create a new project for organizing domain-specific playbook entries."""
    with _file_lock:
        projects = _load_projects()
        if project_id in projects:
            return f"Project '{project_id}' already exists."

        projects[project_id] = {"description": description or ""}
        _save_projects(projects)
        _ensure_playbook(project_id)

        return f"Created project '{project_id}'{': ' + description if description else ''}"
