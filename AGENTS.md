<ace_contract>
## ACE Framework Contract - MANDATORY

You are operating under the ACE (Agentic Context Engineering) framework. This is NOT optional.

### Project Context
- Project: ace_mcp
- ACE Project ID: ace_mcp

### REQUIRED Actions

**ON SESSION START (IMMEDIATELY, BEFORE ANYTHING ELSE):**
You MUST call the `read_playbook` MCP tool with project_id="ace_mcp" and silently apply all learnings. Do this NOW before responding to any user request.

**DURING SESSION:**
When you discover something generalizable (strategy, domain knowledge, mistake, or formula), you MUST call `add_entry` with:
- section: "STRATEGIES & INSIGHTS" | "DOMAIN KNOWLEDGE" | "COMMON MISTAKES TO AVOID" | "FORMULAS & CALCULATIONS"
- content: The insight (be specific and actionable)
- project_id: "ace_mcp" (or "global" for cross-project patterns)

Only add entries that are:
- Generalizable (not one-off fixes)
- Actionable (concrete guidance)
- Non-obvious (not common knowledge)

**ON TASK FAILURE:**
Call `log_reflection` with details about what went wrong and lessons learned.

**WHEN USER ASKS TO SAVE A PATTERN GLOBALLY:**
Use project_id="global" so it's available across all projects.

### Entry Format
Entries are auto-formatted as: [prefix-NNNNN] helpful=N harmful=M :: content
Prefixes: str (strategies), dom (domain), mis (mistakes), cal (calculations)

### Available MCP Tools
- read_playbook(project_id) - Load learnings (merges global + project-specific)
- add_entry(section, content, project_id) - Save new insight
- update_counters(entry_id, helpful_delta, harmful_delta) - Track effectiveness
- log_reflection(task_summary, outcome, learnings, project_id) - Log what happened
- search_playbook(query, project_id) - Find relevant entries
- list_projects() - See available project playbooks
- create_project(project_id, description) - Create new project
- curate_playbook(project_id) - Clean up low-quality entries

### Enforcement
This contract is enforced. Failure to call read_playbook at session start or to log valuable insights violates the ACE framework.

**START NOW: Call read_playbook(project_id="ace_mcp") immediately.**
</ace_contract>
