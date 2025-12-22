# Multi-Client Configuration

ACE MCP server supports multiple AI clients through dual transport endpoints.

## Endpoints

| Endpoint | Transport | Clients |
|----------|-----------|---------|
| `/sse` | SSE (legacy) | Claude Code, Claude Desktop |
| `/mcp` | Streamable HTTP | ChatGPT, OpenAI Codex CLI, OpenAI Agents SDK |

## Claude Code

```bash
claude mcp add --transport sse ace https://ace-mcp.terry-yodaiken.workers.dev/sse
```

Or use the `claude-ace` wrapper:

```bash
claude-ace setup
claude-ace --dangerously-skip-permissions --resume
```

## OpenAI Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.ace]
url = "https://ace-mcp.terry-yodaiken.workers.dev/mcp"

# Optional: Enable Rust MCP client for better Streamable HTTP support
[features]
rmcp_client = true
```

Then use Codex normally:

```bash
codex
# In session, ACE tools are available
```

## ChatGPT (Developer Mode)

1. Enable Developer Mode: Settings → Connectors → Advanced → Developer Mode
2. Create connector: Settings → Connectors → Create
3. Enter URL: `https://ace-mcp.terry-yodaiken.workers.dev/mcp`
4. Name it "ACE Playbook"
5. OAuth settings:
   - Authorization URL: `https://ace-mcp.terry-yodaiken.workers.dev/oauth/authorize`
   - Token URL: `https://ace-mcp.terry-yodaiken.workers.dev/oauth/token`
   - Client ID/Secret: use the values configured in Worker secrets

The connector will appear in chat via the "Use Connectors" menu.

## OpenAI Agents SDK

```python
from agents import Agent, HostedMCPTool, Runner

agent = Agent(
    name="ACE-enabled Assistant",
    tools=[
        HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "ace",
                "server_url": "https://ace-mcp.terry-yodaiken.workers.dev/mcp",
                "require_approval": "never",
            }
        )
    ],
)

result = await Runner.run(agent, "List all ACE projects")
print(result.final_output)
```

## Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ace": {
      "url": "https://ace-mcp.terry-yodaiken.workers.dev/sse"
    }
  }
}
```

**Note:** Claude Desktop may require `npx mcp-remote` proxy for remote SSE servers. Check Claude Desktop docs for current support.

## Programmatic Access (curl)

### Health Check

```bash
curl https://ace-mcp.terry-yodaiken.workers.dev/health
```

### SSE Transport (Claude-style)

```bash
# Establish SSE connection
curl -N https://ace-mcp.terry-yodaiken.workers.dev/sse
```

If `REQUIRE_AUTH=true`, include:

```bash
curl -N https://ace-mcp.terry-yodaiken.workers.dev/sse \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Streamable HTTP (OpenAI-style)

```bash
# Initialize session
curl -X POST https://ace-mcp.terry-yodaiken.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {"name": "curl-test", "version": "1.0"}
    }
  }'
```

## Available Tools

All tools are available on both transports:

| Tool | Description |
|------|-------------|
| `read_playbook` | Load playbook entries |
| `get_section` | Get specific section |
| `add_entry` | Add new insight |
| `update_counters` | Track effectiveness |
| `remove_entry` | Delete entry |
| `log_reflection` | Log task outcome |
| `search_playbook` | Search entries |
| `list_projects` | List all projects |
| `create_project` | Create new project |
| `curate_playbook` | Remove low-quality entries |

## Troubleshooting

### ChatGPT: "Connector not responding"

Verify the endpoint is accessible:

```bash
curl -X POST https://ace-mcp.terry-yodaiken.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'
```

### Codex: "MCP server not found"

Check config syntax:

```bash
cat ~/.codex/config.toml | grep -A5 "ace"
```

Ensure you're using `url` not `command` for remote servers.

### Claude Code: "Connection failed"

```bash
claude mcp list  # Verify ace is registered
claude mcp remove ace
claude mcp add --transport sse ace https://ace-mcp.terry-yodaiken.workers.dev/sse
```
