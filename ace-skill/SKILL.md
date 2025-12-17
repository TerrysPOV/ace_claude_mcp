---
name: ace
description: "Agentic Context Engineering - automated self-improvement through evolving playbooks. Use when: (1) Starting task-oriented conversations - read playbook silently, (2) After task completion - update counters and log learnings, (3) User mentions playbook/learning/memory/ACE, (4) New reusable pattern identified - add entry, (5) Periodic maintenance - curate playbook. Requires ace-mcp server connected."
---

# Agentic Context Engineering (ACE)

Evolve a persistent playbook of strategies, insights, and mistakes to improve performance across conversations.

## Startup

At conversation start, call `read_playbook(project_id)` silently. Apply retrieved entries without mentioning them unless directly relevant.

## Project Selection

| Context | project_id |
|---------|------------|
| Financial/regulatory | `finance` |
| Code/development | `dev` |
| General/unclear | `global` |

## Task Execution

1. Apply relevant playbook entries
2. Track which entries helped or misled
3. Watch for new generalizable patterns

## Post-Task Actions

### On Success
```
update_counters(entry_id, helpful_delta=1, harmful_delta=0)  # for each helpful entry
add_entry(section, content, project_id)  # if new pattern emerged
```

### On Failure/Correction
```
log_reflection(task_summary, "failed", [learnings], project_id)
update_counters(entry_id, helpful_delta=0, harmful_delta=1)  # for misleading entries
add_entry("COMMON MISTAKES TO AVOID", lesson, project_id)  # if applicable
```

## Entry Quality Filter

Add only if ALL true:
- **Generalizable** - applies beyond this task
- **Actionable** - specific enough to use
- **Non-obvious** - not common knowledge

## Section Taxonomy

| Section | Prefix | Use For |
|---------|--------|---------|
| STRATEGIES & INSIGHTS | `str` | Approaches, heuristics |
| FORMULAS & CALCULATIONS | `cal` | Computations, algorithms |
| COMMON MISTAKES TO AVOID | `mis` | Pitfalls, antipatterns |
| DOMAIN KNOWLEDGE | `dom` | Facts, regulations |

## Curation

After 5+ reflections in session, run `curate_playbook(project_id)`.

For manual curation or debugging, run: `python scripts/curate.py <playbook_path> --threshold 3`

## Format Reference

See [references/playbook-format.md](references/playbook-format.md) for entry format, counter logic, and multi-project architecture.

## Transparency

Discuss playbook only when user explicitly asks. Otherwise apply knowledge silently.
