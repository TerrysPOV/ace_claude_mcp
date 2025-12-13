"""
ACE (Agentic Context Engineering) MCP Server

A FastMCP server that provides tools for managing an evolving playbook -
a structured text file that improves LLM context through reflection and curation.
"""

from fastmcp import FastMCP

import ace_core

# Initialize FastMCP server
mcp = FastMCP("ace")


@mcp.tool()
def read_playbook() -> str:
    """
    Return the full current playbook content.

    Use this to see all strategies, formulas, mistakes, and domain knowledge
    that have been accumulated. The playbook is the evolving context that
    helps improve task performance over time.
    """
    return ace_core.read_playbook()


@mcp.tool()
def get_section(section: str) -> str:
    """
    Get all entries from a specific section of the playbook.

    Args:
        section: The section name. One of:
            - "STRATEGIES & INSIGHTS"
            - "FORMULAS & CALCULATIONS"
            - "COMMON MISTAKES TO AVOID"
            - "DOMAIN KNOWLEDGE"

    Returns:
        The entries in that section, or an error message if section not found.
    """
    return ace_core.get_section(section)


@mcp.tool()
def add_entry(section: str, content: str) -> str:
    """
    Add a new entry to the playbook with auto-generated ID and counters set to 0.

    Use this after learning something new - a useful strategy, formula,
    common mistake to avoid, or domain-specific knowledge.

    Args:
        section: The section to add to. One of:
            - "STRATEGIES & INSIGHTS"
            - "FORMULAS & CALCULATIONS"
            - "COMMON MISTAKES TO AVOID"
            - "DOMAIN KNOWLEDGE"
        content: The insight, formula, or knowledge to add.

    Returns:
        Confirmation message with the new entry ID.
    """
    return ace_core.add_entry(section, content)


@mcp.tool()
def update_counters(entry_id: str, helpful_delta: int, harmful_delta: int) -> str:
    """
    Update the helpful/harmful counters for an entry.

    Call this after using an entry to track whether it was helpful or harmful.
    Positive deltas increase counters, negative deltas decrease them.
    Counters cannot go below 0.

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
    superseded by better insights.

    Args:
        entry_id: The entry ID to remove (e.g., "str-00001")

    Returns:
        Confirmation message or error if entry not found.
    """
    return ace_core.remove_entry(entry_id)


@mcp.tool()
def log_reflection(task_summary: str, outcome: str, learnings: list[str]) -> str:
    """
    Log a task reflection for later curation into the playbook.

    After completing a task, use this to record what happened and what was
    learned. These reflections can later be reviewed and curated into
    proper playbook entries.

    Args:
        task_summary: Brief description of the task performed
        outcome: The result - "success", "partial", or "failure"
        learnings: List of insights, strategies, or mistakes identified

    Returns:
        Confirmation that the reflection was logged.
    """
    return ace_core.log_reflection(task_summary, outcome, learnings)


@mcp.tool()
def curate_playbook(harmful_threshold: int = 3) -> str:
    """
    Curate the playbook by removing harmful entries and deduplicating.

    This performs two operations:
    1. Removes entries where harmful > helpful + threshold
    2. Identifies and reports similar entries (>80% similarity) for manual review

    Run this periodically to keep the playbook clean and effective.

    Args:
        harmful_threshold: Remove entries where harmful exceeds helpful by this amount.
                          Default is 3.

    Returns:
        Summary of curation actions taken.
    """
    return ace_core.curate_playbook(harmful_threshold)


@mcp.tool()
def search_playbook(query: str) -> str:
    """
    Search the playbook for entries containing the query keywords.

    Use this to find relevant strategies, formulas, or knowledge before
    starting a task, or to check if similar insights already exist.

    Args:
        query: Keywords to search for (case-insensitive)

    Returns:
        Matching entries or a message if none found.
    """
    return ace_core.search_playbook(query)


if __name__ == "__main__":
    mcp.run()
