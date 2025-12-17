"""
ACE (Agentic Context Engineering) MCP Server - Local Mode

A FastMCP server that provides tools for managing an evolving playbook -
a structured text file that improves LLM context through reflection and curation.
Supports multi-project playbooks with global + project-specific entries.
"""

from typing import Optional
from fastmcp import FastMCP

import ace_core

# Initialize FastMCP server
mcp = FastMCP("ace")


@mcp.tool()
def read_playbook(project_id: str = "global") -> str:
    """
    Return the full playbook content, merging global entries with project-specific entries.

    Args:
        project_id: Project ID to read (default: 'global'). When reading a specific
                   project, global entries are included first, then project entries.

    Returns:
        The formatted playbook content as markdown.
    """
    return ace_core.read_playbook(project_id)


@mcp.tool()
def get_section(section: str, project_id: str = "global") -> str:
    """
    Get all entries from a specific section of the playbook.

    Args:
        section: The section name. One of:
            - "STRATEGIES & INSIGHTS"
            - "FORMULAS & CALCULATIONS"
            - "COMMON MISTAKES TO AVOID"
            - "DOMAIN KNOWLEDGE"
        project_id: Project ID (default: includes global + this project)

    Returns:
        The entries in that section, or an error message if section not found.
    """
    return ace_core.get_section(section, project_id)


@mcp.tool()
def add_entry(section: str, content: str, project_id: str = "global") -> str:
    """
    Add a new entry to the playbook with auto-generated ID and counters set to 0.

    Use 'global' project_id for universal patterns that apply everywhere.
    Use a specific project_id for domain-specific knowledge.

    Args:
        section: The section to add to. One of:
            - "STRATEGIES & INSIGHTS"
            - "FORMULAS & CALCULATIONS"
            - "COMMON MISTAKES TO AVOID"
            - "DOMAIN KNOWLEDGE"
        content: The insight, formula, or knowledge to add.
        project_id: Project ID (default: 'global' for universal patterns)

    Returns:
        Confirmation message with the new entry ID.
    """
    return ace_core.add_entry(section, content, project_id)


@mcp.tool()
def update_counters(entry_id: str, helpful_delta: int, harmful_delta: int) -> str:
    """
    Update the helpful/harmful counters for an entry.

    Call this after using an entry to track whether it was helpful or harmful.
    Positive deltas increase counters, negative deltas decrease them.
    Counters cannot go below 0. Entry ID is unique across all projects.

    Args:
        entry_id: The entry ID (e.g., "str-00001")
        helpful_delta: Amount to add to helpful counter (can be negative)
        harmful_delta: Amount to add to harmful counter (can be negative)

    Returns:
        Confirmation with new counter values, or error if entry not found.
    """
    return ace_core.update_counters(entry_id, helpful_delta, harmful_delta)


@mcp.tool()
def remove_entry(entry_id: str) -> str:
    """
    Remove an entry from the playbook by its ID.

    Use this to delete entries that are no longer relevant or have been
    superseded by better insights. Entry ID is unique across all projects.

    Args:
        entry_id: The entry ID to remove (e.g., "str-00001")

    Returns:
        Confirmation message or error if entry not found.
    """
    return ace_core.remove_entry(entry_id)


@mcp.tool()
def log_reflection(
    task_summary: str,
    outcome: str,
    learnings: list[str],
    project_id: str = "global"
) -> str:
    """
    Log a task reflection for later curation into the playbook.

    After completing a task, use this to record what happened and what was
    learned. These reflections can later be reviewed and curated into
    proper playbook entries.

    Args:
        task_summary: Brief description of the task performed
        outcome: The result - "success", "partial", or "failure"
        learnings: List of insights, strategies, or mistakes identified
        project_id: Project ID for this reflection (default: 'global')

    Returns:
        Confirmation that the reflection was logged.
    """
    return ace_core.log_reflection(task_summary, outcome, learnings, project_id)


@mcp.tool()
def curate_playbook(
    project_id: Optional[str] = None,
    harmful_threshold: int = 3
) -> str:
    """
    Curate the playbook by removing harmful entries and finding duplicates.

    This performs two operations:
    1. Removes entries where harmful > helpful + threshold
    2. Identifies and reports similar entries (>80% similarity) for manual review

    Run this periodically to keep the playbook clean and effective.

    Args:
        project_id: Project to curate (default: all projects)
        harmful_threshold: Remove entries where harmful exceeds helpful by this amount.
                          Default is 3.

    Returns:
        Summary of curation actions taken.
    """
    return ace_core.curate_playbook(project_id, harmful_threshold)


@mcp.tool()
def search_playbook(query: str, project_id: str = "global") -> str:
    """
    Search the playbook for entries containing the query keywords.

    Use this to find relevant strategies, formulas, or knowledge before
    starting a task, or to check if similar insights already exist.

    Args:
        query: Keywords to search for (case-insensitive, space-separated)
        project_id: Project ID to search within (includes global entries)

    Returns:
        Matching entries or a message if none found.
    """
    return ace_core.search_playbook(query, project_id)


@mcp.tool()
def list_projects() -> str:
    """
    List all projects in the playbook system.

    Returns:
        List of project IDs with their descriptions.
    """
    return ace_core.list_projects()


@mcp.tool()
def create_project(project_id: str, description: Optional[str] = None) -> str:
    """
    Create a new project for organizing domain-specific playbook entries.

    Projects allow you to separate learnings by domain (e.g., 'finance',
    'web-dev', 'data-science') while still benefiting from global patterns.

    Args:
        project_id: Unique project identifier (e.g., 'finance', 'web-dev')
        description: Brief description of the project domain

    Returns:
        Confirmation message or error if project already exists.
    """
    return ace_core.create_project(project_id, description)


if __name__ == "__main__":
    mcp.run()
