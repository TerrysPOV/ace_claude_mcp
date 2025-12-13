# ACE MCP Server

A FastMCP server implementing **Agentic Context Engineering (ACE)** - a framework for LLM self-improvement through evolving context.

## What is ACE?

ACE treats the model's context as a living, evolving **playbook** that gets better over time through:
- **Generation**: Performing tasks and observing outcomes
- **Reflection**: Extracting strategies, patterns, and mistakes
- **Curation**: Pruning harmful entries and deduplicating

Instead of fine-tuning model weights, ACE improves LLM performance by evolving the context - producing human-readable, auditable learning.

## Quick Start

### 1. Install Dependencies

```bash
pip install fastmcp
```

### 2. Run the Server

```bash
# Using FastMCP CLI
fastmcp run ace_server.py

# Or with Python directly
python ace_server.py
```

### 3. Test Locally

```bash
fastmcp dev ace_server.py
```

## Claude.ai MCP Integration

Add this to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ace": {
      "command": "python",
      "args": ["/path/to/ace_server.py"]
    }
  }
}
```

Or using `uvx` (recommended for cleaner environment):

```json
{
  "mcpServers": {
    "ace": {
      "command": "uvx",
      "args": ["--from", "fastmcp", "fastmcp", "run", "/path/to/ace_server.py"]
    }
  }
}
```

Restart Claude Desktop after updating the config.

## Available Tools

| Tool | Description |
|------|-------------|
| `read_playbook()` | Return the full current playbook |
| `get_section(section)` | Get entries from a specific section |
| `add_entry(section, content)` | Add new entry with auto-generated ID |
| `update_counters(entry_id, helpful_delta, harmful_delta)` | Update helpful/harmful counters |
| `remove_entry(entry_id)` | Delete an entry |
| `log_reflection(task_summary, outcome, learnings)` | Log task outcome for later curation |
| `curate_playbook(harmful_threshold)` | Remove harmful entries and find duplicates |
| `search_playbook(query)` | Keyword search across all entries |

## Playbook Format

The playbook is stored at `~/.ace/playbook.md`:

```markdown
## STRATEGIES & INSIGHTS
[str-00001] helpful=5 harmful=0 :: Always verify data types before processing.
[str-00002] helpful=3 harmful=1 :: Consider edge cases in financial data.

## FORMULAS & CALCULATIONS
[cal-00001] helpful=8 harmful=0 :: NPV = Σ(Cash Flow / (1+r)^t)

## COMMON MISTAKES TO AVOID
[mis-00001] helpful=6 harmful=0 :: Don't forget timezone conversions.

## DOMAIN KNOWLEDGE
[dom-00001] helpful=2 harmful=0 :: UK FCA requires firms to maintain capital buffers.
```

Each entry has:
- **ID**: Stable reference (e.g., `str-00001`)
- **helpful/harmful**: Counters updated through feedback
- **Content**: The actual strategy, insight, or formula

## Workflow Example

### 1. Before a Task - Search Relevant Context
```
search_playbook("data validation")
```

### 2. After Success - Add Learning
```
add_entry("STRATEGIES & INSIGHTS", "Use schema validation for API responses to catch type mismatches early.")
```

### 3. Track Effectiveness
```
update_counters("str-00003", helpful_delta=1, harmful_delta=0)
```

### 4. Log Detailed Reflection
```
log_reflection(
    task_summary="Implemented user authentication",
    outcome="success",
    learnings=["JWT refresh tokens prevent session expiry issues", "Always hash passwords with bcrypt, not MD5"]
)
```

### 5. Periodic Curation
```
curate_playbook(harmful_threshold=3)
```

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Playbook | `~/.ace/playbook.md` | Main context file |
| Reflections | `~/.ace/reflections.jsonl` | Task reflections for later curation |

## Cloudflare Workers Deployment

The server is structured for easy deployment to Cloudflare Workers. Use the FastMCP deployment guide:

```bash
fastmcp deploy ace_server.py --name ace-server
```

## References

- [ACE Paper](https://medium.com/coding-nexus/agentic-context-engineering-ace-the-powerful-new-way-for-llms-to-self-improve-93b9559432a2)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol](https://modelcontextprotocol.io)

## License

MIT
