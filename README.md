# ACE Claude MCP

**Agentic Context Engineering (ACE)** - A self-improving knowledge system for AI coding assistants that learns from every session.

ACE provides persistent, cross-project learning via an MCP server. Claude/ChatGPT automatically reads accumulated wisdom at session start and logs new insights during work.

## Multi-Client Support

ACE supports **multiple AI clients** through dual transport endpoints:

| Endpoint | Transport | Clients |
|----------|-----------|---------|
| `/sse` | SSE (legacy) | Claude Code, Claude Desktop |
| `/mcp` | Streamable HTTP | ChatGPT, OpenAI Codex CLI |

**Production URL:** `https://ace-mcp.terry-yodaiken.workers.dev`

## Architecture

Two deployment options:

| Component | Storage | Use Case |
|-----------|---------|----------|
| **Cloudflare Workers + D1** | SQLite (D1) | Production - persistent, accessible anywhere |
| **Local Python Server** | Markdown files | Development - file-based at `~/.ace/playbooks/` |

## Quick Start (Cloudflare - Recommended)

### 1. Install the Wrapper

```bash
cd claude-ace-mcp
./install.sh
```

Or manually:

```bash
mkdir -p ~/.ace/bin
cp claude-ace-mcp/bin/claude-ace ~/.ace/bin/
chmod +x ~/.ace/bin/claude-ace

# Add to PATH
echo 'export PATH="$HOME/.ace/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 2. Run Setup

```bash
claude-ace setup
```

This will:
1. Prompt for your `ANTHROPIC_API_KEY` (get one at https://console.anthropic.com/settings/keys)
2. Save it to your shell profile (`.zshrc`/`.bashrc`)
3. Configure the MCP server via `claude mcp add`

### 3. Start a Session

```bash
cd your-project
claude-ace
```

With options:
```bash
claude-ace --dangerously-skip-permissions --resume
claude-ace -p "fix the bug"
claude-ace --project-id finance
```

## How It Works

The wrapper:
1. Detects project type from directory name or `CLAUDE.md`
2. Injects an ACE contract via `--append-system-prompt`
3. Claude **must** call `read_playbook` at session start
4. Claude logs insights during the session via `add_entry`

### Project Detection

| Project ID | Keywords |
|------------|----------|
| `finance` | regulatory, compliance, fund, investment, mifid, fca, ucits, poview |
| `dev` | code, programming, api, backend, frontend, deploy |
| `global` | (default fallback) |

## MCP Tools

| Tool | Description |
|------|-------------|
| `read_playbook(project_id?)` | Load learnings (merges global + project-specific) |
| `add_entry(section, content, project_id?)` | Save new insight |
| `update_counters(entry_id, helpful_delta, harmful_delta)` | Track effectiveness |
| `log_reflection(task_summary, outcome, learnings, project_id?)` | Log session reflection |
| `search_playbook(query, project_id?)` | Find relevant entries |
| `list_projects()` | List available projects |
| `create_project(project_id, description?)` | Create new project |
| `curate_playbook(project_id?, harmful_threshold?)` | Clean up low-quality entries |

### Entry Sections

- `STRATEGIES & INSIGHTS` - Approaches that work
- `DOMAIN KNOWLEDGE` - Facts and context
- `COMMON MISTAKES TO AVOID` - Pitfalls learned
- `FORMULAS & CALCULATIONS` - Reusable computations

## Cloudflare Deployment

### Prerequisites

- Node.js 18+
- Wrangler CLI (`npm install -g wrangler`)
- Cloudflare account

### Deploy

```bash
# Install dependencies
npm install

# Login to Cloudflare
wrangler login

# Create D1 database (first time only)
wrangler d1 create ace-playbook

# Apply schema
wrangler d1 execute ace-playbook --remote --file=schema.sql

# Deploy
npm run deploy
```

### OAuth Setup (Google + ChatGPT)

Set secrets before deploying:

```bash
wrangler secret put GOOGLE_CLIENT_ID
wrangler secret put GOOGLE_CLIENT_SECRET
wrangler secret put GOOGLE_REDIRECT_URI
wrangler secret put OAUTH_CLIENT_ID
wrangler secret put OAUTH_CLIENT_SECRET
wrangler secret put OAUTH_REDIRECT_URIS
wrangler secret put JWT_SECRET

# Optional
wrangler secret put REQUIRE_AUTH
wrangler secret put DEFAULT_USER_ID
```

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /sse` | SSE endpoint for MCP |
| `GET /oauth/authorize` | OAuth authorization endpoint |
| `GET /oauth/callback` | OAuth callback endpoint |
| `POST /oauth/token` | OAuth token exchange endpoint |

**Production URL:** `https://ace-mcp.terry-yodaiken.workers.dev`

### Connect Claude Code Directly

Without the wrapper, you can add the MCP server directly:

```bash
claude mcp add --transport sse ace https://ace-mcp.terry-yodaiken.workers.dev/sse
```

### Connect OpenAI Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.ace]
url = "https://ace-mcp.terry-yodaiken.workers.dev/mcp"

[features]
rmcp_client = true
```

### Global AGENTS Template + codex-init

Set a global ACE contract template and a project bootstrap script:

- Global template: `~/.codex/AGENTS.md`
- Script: `~/.local/bin/codex-init`

Usage in any project root:

```bash
# Uses the folder name as the project_id by default
codex-init

# Override the project_id
ACE_PROJECT_ID=finance codex-init
```

`codex-init` copies `~/.codex/AGENTS.md` into `./AGENTS.md`, substitutes
`{project_name}` and `{project_id}`, then launches `codex` if available.

### Connect ChatGPT (Developer Mode)

1. Enable: Settings → Connectors → Advanced → Developer Mode
2. Create: Settings → Connectors → Create
3. URL: `https://ace-mcp.terry-yodaiken.workers.dev/mcp`
4. Name: "ACE Playbook"
5. OAuth settings:
   - Authorization URL: `https://ace-mcp.terry-yodaiken.workers.dev/oauth/authorize`
   - Token URL: `https://ace-mcp.terry-yodaiken.workers.dev/oauth/token`
   - Client ID/Secret: use the values configured in Worker secrets

## Local Python Server (Alternative)

For local development with file-based storage:

```bash
# Install
pip install fastmcp

# Run
uvx --from fastmcp fastmcp run ace_server.py
```

Storage location: `~/.ace/playbooks/`

**Note:** Local server uses markdown files, not SQLite. The wrapper is designed for the Cloudflare deployment.

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Required for Claude Code |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Google OAuth redirect URI (points to `/oauth/callback`) |
| `OAUTH_CLIENT_ID` | OAuth client ID for ChatGPT connector |
| `OAUTH_CLIENT_SECRET` | OAuth client secret for ChatGPT connector |
| `OAUTH_REDIRECT_URIS` | Comma-separated allowed redirect URIs |
| `JWT_SECRET` | HMAC secret for access tokens/state |
| `REQUIRE_AUTH` | `true` to require OAuth for `/mcp` and `/sse` |
| `DEFAULT_USER_ID` | Fallback user ID for legacy clients without OAuth |

### Files

| File | Purpose |
|------|---------|
| `wrangler.toml` | Cloudflare Workers config |
| `schema.sql` | D1 database schema |
| `src/index.ts` | Worker entry point |
| `ace_server.py` | Local Python MCP server |
| `ace_core.py` | Local file-based storage logic |

## Wrapper Commands

```bash
claude-ace                    # Start interactive session
claude-ace setup              # Configure API key + MCP server
claude-ace status             # Check configuration
claude-ace -p "prompt"        # One-shot prompt
claude-ace --resume           # Resume last session
claude-ace --continue         # Continue last session
claude-ace --project-id X     # Force specific project ID
claude-ace -C /path           # Specify project directory
claude-ace --model MODEL      # Use specific model
claude-ace --dangerously-skip-permissions  # Skip permission prompts
```

## Troubleshooting

### "MCP server not configured"
```bash
claude-ace setup
```

### "ANTHROPIC_API_KEY not found"
```bash
claude-ace setup  # Will prompt for key
# Or manually:
export ANTHROPIC_API_KEY="sk-ant-..."
```

### SSE connection issues
```bash
# Test endpoint
curl https://ace-mcp.terry-yodaiken.workers.dev/health
curl -v https://ace-mcp.terry-yodaiken.workers.dev/sse
```

### Check MCP is registered
```bash
claude mcp list
```

## License

MIT
