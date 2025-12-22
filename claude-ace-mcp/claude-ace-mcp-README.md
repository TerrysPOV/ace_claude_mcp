# claude-ace (MCP Version)

**Enforced ACE framework for Claude Code** using the `ace_claude_mcp` Cloudflare Worker.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     claude-ace wrapper                       │
│  1. Prompts for ANTHROPIC_API_KEY if not set                │
│  2. Configures MCP server via `claude mcp add`              │
│  3. Injects strict ACE contract via --append-system-prompt  │
│  4. Contract REQUIRES Claude to call read_playbook first    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code + MCP                         │
│  - Receives contract as system prompt                       │
│  - MUST call ACE MCP tools per contract                     │
│  - Full SQLite backend via Cloudflare D1                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Cloudflare Worker (ace-mcp)                     │
│  Endpoint: https://ace-mcp.terry-yodaiken.workers.dev/sse   │
│  - read_playbook(project_id)                                │
│  - add_entry(section, content, project_id)                  │
│  - log_reflection(task, outcome, learnings)                 │
│  - Storage: Cloudflare D1 (SQLite)                          │
└─────────────────────────────────────────────────────────────┘
```

## The Contract

The wrapper injects this strict contract:

```
ON SESSION START (IMMEDIATELY):
  You MUST call read_playbook(project_id) before anything else.

DURING SESSION:
  When you discover something generalizable, you MUST call add_entry().

ON TASK FAILURE:
  Call log_reflection() with details.

FOR GLOBAL PATTERNS:
  Use project_id="global" to share across projects.
```

This is **enforcement**, not suggestion. Claude is contractually obligated.

## Installation

```bash
cd claude-ace-mcp
chmod +x install.sh
./install.sh

# Add to PATH
echo 'export PATH="$HOME/.ace/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Or manually:

```bash
mkdir -p ~/.ace/bin
cp bin/claude-ace ~/.ace/bin/
chmod +x ~/.ace/bin/claude-ace
```

## Setup

```bash
claude-ace setup
```

This will:

1. **Check for `ANTHROPIC_API_KEY`** - prompts if not set
2. **Save to shell profile** - adds `export ANTHROPIC_API_KEY="..."` to `.zshrc`/`.bashrc`
3. **Configure MCP server** - runs `claude mcp add --transport sse ace <url>`

Get your API key at: https://console.anthropic.com/settings/keys

## Usage

```bash
# Start interactive session
claude-ace

# With permissions skip
claude-ace --dangerously-skip-permissions

# Resume previous session
claude-ace --resume

# Combined
claude-ace --dangerously-skip-permissions --resume

# One-shot prompt
claude-ace -p "fix the authentication bug"

# Force specific project ID
claude-ace --project-id finance

# Specify project directory
claude-ace -C ~/projects/my-app

# Check status
claude-ace status
```

## Project ID Detection

The wrapper auto-detects project type from directory name or `CLAUDE.md`:

| Keywords | Project ID |
|----------|------------|
| regulatory, compliance, fund, investment, mifid, fca, ucits, poview | `finance` |
| code, programming, api, backend, frontend, deploy | `dev` |
| (default) | `global` |

Override with `--project-id`.

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `read_playbook(project_id?)` | Load learnings (merges global + project) |
| `add_entry(section, content, project_id?)` | Save new insight |
| `update_counters(entry_id, helpful_delta, harmful_delta)` | Track effectiveness |
| `log_reflection(task_summary, outcome, learnings, project_id?)` | Log what happened |
| `search_playbook(query, project_id?)` | Find relevant entries |
| `list_projects()` | See available playbooks |
| `create_project(project_id, description?)` | Create new project |
| `curate_playbook(project_id?)` | Clean up low-quality entries |

### Entry Sections

- `STRATEGIES & INSIGHTS`
- `DOMAIN KNOWLEDGE`
- `COMMON MISTAKES TO AVOID`
- `FORMULAS & CALCULATIONS`

## Global Patterns

Save patterns for reuse across projects:

```
User: "Save this auth pattern globally"
Claude: [calls add_entry(section="STRATEGIES & INSIGHTS", content="...", project_id="global")]
```

Use in another project:

```
User: "Use the standard auth pattern from global"
Claude: [calls search_playbook(query="auth pattern", project_id="global")]
```

## Troubleshooting

### "MCP server not configured"
```bash
claude-ace setup
```

### "ANTHROPIC_API_KEY not found" but key is in .zshrc
```bash
source ~/.zshrc
# Then retry
claude-ace setup
```

### Check MCP is registered
```bash
claude mcp list
```

### Test the endpoint
```bash
curl https://ace-mcp.terry-yodaiken.workers.dev/health
```

## Requirements

- Claude Code CLI
- Python 3.9+
- `ANTHROPIC_API_KEY`

## Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `ANTHROPIC_API_KEY` | Required for Claude Code |

| Endpoint | URL |
|----------|-----|
| ACE MCP Server | `https://ace-mcp.terry-yodaiken.workers.dev/sse` |

## License

MIT
