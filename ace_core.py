"""
ACE Core Logic - Pure functions without MCP dependencies.

This module contains all the business logic for the ACE playbook system,
separated from the MCP server for testability.
"""

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

# Configuration
ACE_DIR = Path.home() / ".ace"
PLAYBOOK_PATH = ACE_DIR / "playbook.md"
REFLECTIONS_PATH = ACE_DIR / "reflections.jsonl"

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


def _ensure_ace_dir():
    """Create ACE directory if it doesn't exist."""
    ACE_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_playbook():
    """Create playbook with default content if it doesn't exist."""
    _ensure_ace_dir()
    if not PLAYBOOK_PATH.exists():
        PLAYBOOK_PATH.write_text(DEFAULT_PLAYBOOK, encoding="utf-8")


def _read_playbook_content() -> str:
    """Read playbook content, creating default if needed."""
    _ensure_playbook()
    return PLAYBOOK_PATH.read_text(encoding="utf-8")


def _write_playbook_content(content: str):
    """Write content to playbook file."""
    _ensure_ace_dir()
    PLAYBOOK_PATH.write_text(content, encoding="utf-8")


def _parse_entry(line: str) -> dict | None:
    """Parse a playbook entry line into components."""
    pattern = r"\[([a-z]{3}-\d{5})\]\s+helpful=(\d+)\s+harmful=(\d+)\s+::\s+(.+)"
    match = re.match(pattern, line.strip())
    if match:
        return {
            "id": match.group(1),
            "helpful": int(match.group(2)),
            "harmful": int(match.group(3)),
            "content": match.group(4),
        }
    return None


def _format_entry(entry_id: str, helpful: int, harmful: int, content: str) -> str:
    """Format an entry as a playbook line."""
    return f"[{entry_id}] helpful={helpful} harmful={harmful} :: {content}"


def _get_next_id(content: str, prefix: str) -> str:
    """Generate the next available ID for a section."""
    pattern = rf"\[{prefix}-(\d{{5}})\]"
    matches = re.findall(pattern, content)
    if matches:
        max_num = max(int(m) for m in matches)
        return f"{prefix}-{max_num + 1:05d}"
    return f"{prefix}-00001"


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


def read_playbook() -> str:
    """Return the full current playbook content."""
    with _file_lock:
        return _read_playbook_content()


def get_section(section: str) -> str:
    """Get all entries from a specific section of the playbook."""
    valid_sections = list(SECTION_PREFIXES.keys())
    if section not in valid_sections:
        return f"Invalid section. Must be one of: {valid_sections}"

    with _file_lock:
        content = _read_playbook_content()
        _, _, section_lines = _get_section_content(content, section)

        if not section_lines:
            return f"Section '{section}' not found in playbook."

        return "\n".join(section_lines)


def add_entry(section: str, content: str) -> str:
    """Add a new entry to the playbook with auto-generated ID and counters set to 0."""
    if section not in SECTION_PREFIXES:
        return f"Invalid section. Must be one of: {list(SECTION_PREFIXES.keys())}"

    prefix = SECTION_PREFIXES[section]

    with _file_lock:
        playbook_content = _read_playbook_content()
        new_id = _get_next_id(playbook_content, prefix)
        new_entry = _format_entry(new_id, 0, 0, content.strip())

        start_idx, end_idx, section_lines = _get_section_content(
            playbook_content, section
        )

        if start_idx == -1:
            # Section doesn't exist, add it at the end
            playbook_content = (
                playbook_content.rstrip() + f"\n\n## {section}\n{new_entry}\n"
            )
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

        _write_playbook_content(playbook_content)
        return f"Added entry [{new_id}] to '{section}'"


def update_counters(entry_id: str, helpful_delta: int, harmful_delta: int) -> str:
    """Update the helpful/harmful counters for an entry."""
    pattern = rf"\[{re.escape(entry_id)}\]\s+helpful=(\d+)\s+harmful=(\d+)\s+::\s+(.+)"

    with _file_lock:
        content = _read_playbook_content()
        match = re.search(pattern, content)

        if not match:
            return f"Entry '{entry_id}' not found in playbook."

        old_helpful = int(match.group(1))
        old_harmful = int(match.group(2))
        entry_content = match.group(3)

        new_helpful = max(0, old_helpful + helpful_delta)
        new_harmful = max(0, old_harmful + harmful_delta)

        new_entry = _format_entry(entry_id, new_helpful, new_harmful, entry_content)
        new_content = re.sub(pattern, new_entry, content)

        _write_playbook_content(new_content)
        return f"Updated [{entry_id}]: helpful={old_helpful}->{new_helpful}, harmful={old_harmful}->{new_harmful}"


def remove_entry(entry_id: str) -> str:
    """Remove an entry from the playbook by its ID."""
    pattern = rf"^\[{re.escape(entry_id)}\]\s+helpful=\d+\s+harmful=\d+\s+::.*$"

    with _file_lock:
        content = _read_playbook_content()
        lines = content.split("\n")
        new_lines = []
        found = False

        for line in lines:
            if re.match(pattern, line.strip()):
                found = True
            else:
                new_lines.append(line)

        if not found:
            return f"Entry '{entry_id}' not found in playbook."

        _write_playbook_content("\n".join(new_lines))
        return f"Removed entry [{entry_id}]"


def log_reflection(task_summary: str, outcome: str, learnings: list[str]) -> str:
    """Log a task reflection for later curation into the playbook."""
    reflection = {
        "timestamp": datetime.now().isoformat(),
        "task_summary": task_summary,
        "outcome": outcome,
        "learnings": learnings,
    }

    with _file_lock:
        _ensure_ace_dir()
        with open(REFLECTIONS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(reflection) + "\n")

    return f"Logged reflection with {len(learnings)} learning(s) for task: {task_summary[:50]}..."


def curate_playbook(harmful_threshold: int = 3) -> str:
    """Curate the playbook by removing harmful entries and deduplicating."""
    with _file_lock:
        content = _read_playbook_content()
        lines = content.split("\n")
        new_lines = []
        removed = []
        entries = []

        # First pass: remove harmful entries, collect valid entries
        for line in lines:
            entry = _parse_entry(line)
            if entry:
                if entry["harmful"] > entry["helpful"] + harmful_threshold:
                    removed.append(entry["id"])
                else:
                    new_lines.append(line)
                    entries.append(entry)
            else:
                new_lines.append(line)

        # Second pass: find duplicates (for reporting, not auto-removing)
        duplicates = []
        for i, e1 in enumerate(entries):
            for e2 in entries[i + 1 :]:
                sim = _similarity(e1["content"], e2["content"])
                if sim > 0.8:
                    duplicates.append((e1["id"], e2["id"], f"{sim:.0%}"))

        _write_playbook_content("\n".join(new_lines))

        result = []
        if removed:
            result.append(f"Removed {len(removed)} harmful entries: {removed}")
        else:
            result.append("No harmful entries to remove.")

        if duplicates:
            dup_report = "; ".join(
                [f"{d[0]} ~ {d[1]} ({d[2]})" for d in duplicates[:5]]
            )
            result.append(f"Potential duplicates found: {dup_report}")
            if len(duplicates) > 5:
                result.append(f"  ...and {len(duplicates) - 5} more")
        else:
            result.append("No duplicate entries found.")

        return "\n".join(result)


def search_playbook(query: str) -> str:
    """Search the playbook for entries containing the query keywords."""
    with _file_lock:
        content = _read_playbook_content()

    query_lower = query.lower()
    keywords = query_lower.split()
    matches = []

    for line in content.split("\n"):
        entry = _parse_entry(line)
        if entry:
            content_lower = entry["content"].lower()
            if any(kw in content_lower for kw in keywords):
                matches.append(line.strip())

    if not matches:
        return f"No entries found matching '{query}'"

    return f"Found {len(matches)} matching entries:\n" + "\n".join(matches)
