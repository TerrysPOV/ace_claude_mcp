# ACE MCP Server

A FastMCP server implementing **Agentic Context Engineering (ACE)** - a framework for LLM self-improvement through evolving context.

## What is ACE?

ACE treats the model's context as a living, evolving **playbook** that gets better over time through:
- **Generation**: Performing tasks and observing outcomes
- **Reflection**: Extracting strategies, patterns, and mistakes
- **Curation**: Pruning harmful entries and deduplicating

Instead of fine-tuning model weights, ACE improves LLM performance by evolving the context - producing human-readable, auditable learning.

## Deployment Options

| Mode | Storage | Multi-project | Best For |
|------|---------|---------------|----------|
| **Local** | File-based (`~/.ace/`) | Yes | Single user, local development |
| **Cloud** | Cloudflare D1 | Yes | Teams, production, multi-user |

---

## Local Mode (Python)

### Quick Start

```bash
pip install fastmcp

# Run the server
python ace_server.py

# Or use FastMCP CLI
fastmcp run ace_server.py
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

### File Structure (Local Mode)

```
~/.ace/
├── playbooks/
│   ├── global.md           # Universal patterns
│   ├── finance.md          # Project-specific
│   └── web-dev.md          # Project-specific
├── reflections/
│   ├── global.jsonl
│   └── finance.jsonl
└── projects.json           # Project metadata
```

---

## Cloud Mode (Cloudflare Workers + D1)

### Prerequisites

- [Node.js](https://nodejs.org/) 18+
- [Cloudflare account](https://dash.cloudflare.com/sign-up)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)

### Setup

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Create D1 database**
   ```bash
   wrangler d1 create ace-playbook
   ```
   Copy the `database_id` from the output.

3. **Update wrangler.toml**
   ```toml
   [[d1_databases]]
   binding = "DB"
   database_name = "ace-playbook"
   database_id = "<YOUR-DATABASE-ID>"
   ```

4. **Apply schema**
   ```bash
   # Local development
   wrangler d1 execute ace-playbook --local --file=schema.sql

   # Production
   wrangler d1 execute ace-playbook --file=schema.sql
   ```

5. **Deploy**
   ```bash
   # Local development
   npm run dev

   # Production deployment
   npm run deploy
   ```

### Claude Desktop Configuration (Cloud)

```json
{
  "mcpServers": {
    "ace": {
      "url": "https://ace-mcp.<your-subdomain>.workers.dev/sse"
    }
  }
}
```

### Migrate Local Data to D1

```bash
# Generate SQL file
python migrate_to_d1.py --output migration.sql

# Review the SQL, then execute
wrangler d1 execute ace-playbook --file=migration.sql

# Or execute directly
python migrate_to_d1.py --execute --database ace-playbook
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `read_playbook(project_id?)` | Return merged global + project playbook |
| `get_section(section, project_id?)` | Get entries from a specific section |
| `add_entry(section, content, project_id?)` | Add new entry with auto-generated ID |
| `update_counters(entry_id, helpful_delta, harmful_delta)` | Update helpful/harmful counters |
| `remove_entry(entry_id)` | Delete an entry |
| `log_reflection(task_summary, outcome, learnings, project_id?)` | Log task outcome |
| `curate_playbook(project_id?, harmful_threshold?)` | Remove harmful entries, find duplicates |
| `search_playbook(query, project_id?)` | Keyword search across entries |
| `list_projects()` | List all projects |
| `create_project(project_id, description?)` | Create a new project |

---

## Multi-Project Playbooks

Projects allow you to organize domain-specific knowledge while sharing global patterns.

### Example: Finance Project

```
# Create a finance project
create_project("finance", "Financial analysis and trading strategies")

# Add domain-specific entry
add_entry("DOMAIN KNOWLEDGE", "UK FCA requires MiFID II best execution reporting", "finance")

# Add universal pattern (goes to global)
add_entry("STRATEGIES & INSIGHTS", "Always validate numerical inputs for edge cases", "global")

# Read finance playbook (includes global + finance entries)
read_playbook("finance")
```

### Playbook Merging Logic

When `read_playbook("finance")` is called:
1. Fetch all entries where `project_id = 'global'`
2. Fetch all entries where `project_id = 'finance'`
3. Merge by section, global entries first, then project-specific
4. Format as markdown with project markers

---

## Playbook Format

```markdown
## STRATEGIES & INSIGHTS
[str-00001] helpful=5 harmful=0 :: Always verify data types before processing.
[str-00002] helpful=3 harmful=1 [finance] :: Consider market hours for time-sensitive operations.

## FORMULAS & CALCULATIONS
[cal-00001] helpful=8 harmful=0 :: NPV = Σ(Cash Flow / (1+r)^t)

## COMMON MISTAKES TO AVOID
[mis-00001] helpful=6 harmful=0 :: Don't forget timezone conversions.

## DOMAIN KNOWLEDGE
[dom-00001] helpful=2 harmful=0 [finance] :: UK FCA requires firms to maintain capital buffers.
```

Each entry has:
- **ID**: Stable reference (e.g., `str-00001`)
- **helpful/harmful**: Counters updated through feedback
- **Project marker**: `[project_id]` for non-global entries
- **Content**: The actual strategy, insight, or formula

---

## Workflow Example

### 1. Before a Task - Load Context
```
read_playbook("finance")
search_playbook("validation", "finance")
```

### 2. After Success - Add Learning
```
add_entry("STRATEGIES & INSIGHTS", "Use schema validation for API responses", "finance")
```

### 3. Track Effectiveness
```
update_counters("str-00003", helpful_delta=1, harmful_delta=0)
```

### 4. Log Detailed Reflection
```
log_reflection(
    task_summary="Implemented trade execution API",
    outcome="success",
    learnings=["Rate limiting prevents API abuse", "Idempotency keys needed for retries"],
    project_id="finance"
)
```

### 5. Periodic Curation
```
curate_playbook("finance", harmful_threshold=3)
```

---

## Database Schema (D1)

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE entries (
    id TEXT PRIMARY KEY,
    project_id TEXT DEFAULT 'global',
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    helpful INTEGER DEFAULT 0,
    harmful INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT DEFAULT 'global',
    task_summary TEXT NOT NULL,
    outcome TEXT NOT NULL,
    learnings TEXT NOT NULL,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Development

### Run Tests

```bash
pip install pytest
pytest test_ace_server.py -v
```

### Local Worker Development

```bash
npm run dev
# Server runs at http://localhost:8787
```

---

## References

- [ACE Paper](https://medium.com/coding-nexus/agentic-context-engineering-ace-the-powerful-new-way-for-llms-to-self-improve-93b9559432a2)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol](https://modelcontextprotocol.io)
- [Cloudflare D1](https://developers.cloudflare.com/d1/)

## License

MIT
