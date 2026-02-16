# Smol Marketing Claw — MCP HTTP Server

Autonomous marketing AI with digital hormone system, SNS posting, and Discord integration — packaged as a Streamable HTTP MCP server.

## Quick Start

```bash
# Install dependencies
pip install -r smol-marketing-claw/requirements.txt

# Start the MCP server (default: http://127.0.0.1:8000)
cd smol-marketing-claw
python -m server.mcp_server
```

On first launch, the server will interactively prompt for any missing API keys and save them to `.env`.

To change the bind address or port:
```bash
MCP_HOST=0.0.0.0 MCP_PORT=9000 python -m server.mcp_server
```

### Connecting via Codex CLI

Add to `.codex/config.toml`:
```toml
[mcp_servers.smol-claw]
type = "http"
url = "http://127.0.0.1:8000/mcp"
```

## Setup

Set environment variables (or create a `.env` file in the project root):

```bash
# X (Twitter) API
X_CONSUMER_KEY="..."
X_CONSUMER_SECRET="..."
X_ACCESS_TOKEN="..."
X_ACCESS_TOKEN_SECRET="..."

# Threads (Meta) API
THREADS_USER_ID="..."
THREADS_ACCESS_TOKEN="..."

# Discord
DISCORD_BOT_TOKEN="..."
DISCORD_CHANNEL_ID="..."
```

Missing keys are prompted interactively at server startup. You can skip any group to use the server without that integration.

## MCP Tools (11)

| Tool | Description |
|------|-------------|
| `smol_claw_status` | Full system status |
| `smol_claw_context` | Git, TODOs, time context |
| `smol_claw_hormone_nudge` | Manual hormone adjustment |
| `smol_claw_think` | Autonomous think cycle |
| `smol_claw_record_outcome` | Record think cycle result |
| `smol_claw_memory_query` | Vector similarity search |
| `smol_claw_post_x` | Post to X/Twitter |
| `smol_claw_reply_x` | Reply on X/Twitter |
| `smol_claw_post_threads` | Post to Threads |
| `smol_claw_reply_threads` | Reply on Threads |
| `smol_claw_discord_control` | Discord bot start/stop/status |

## Architecture

```
smol-marketing-claw/
├── server/                       # MCP HTTP server
│   ├── mcp_server.py            # FastMCP entrypoint (Streamable HTTP)
│   ├── setup.py                 # Interactive .env setup
│   ├── state.py                 # Global state manager
│   └── tools/                   # Tool implementations
├── scripts/                      # Utility scripts
└── requirements.txt
```

The server reuses modules from `src/` (hormones, memory, SNS clients, etc.) without modification. FastMCP provides the Streamable HTTP transport, replacing the previous stdio plugin approach.

## Digital Hormone System

Three-axis emotional state that controls AI behavior:

- **Dopamine** (0-1): Reward signal. High = creative/bold, Low = cautious
- **Cortisol** (0-1): Stress signal. High = defensive, Low = adventurous
- **Energy** (0-1): Resource budget from usage quota remaining

Hormones decay naturally and respond to events (successful posts, errors, user sentiment).
