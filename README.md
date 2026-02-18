# Smol Marketing Claw

<div align="center">
  <img src=".github/crayfish.svg" alt="Cute Crayfish" width="400"/>

  ### *Your tiny, cute AI marketing assistant*

  **A multi-agent Discord system that coordinates SNS marketing across 5 platforms.**

  5 AI bots collaborate in a Discord server to plan, create, and publish marketing content.
</div>

---

[한국어 문서](./README.ko.md)

## Architecture

```
Discord Server
├── #team-room       ← All bots collaborate here via @mentions
├── #captain-room    ← Captain (Team Lead) 1:1 channel
├── #stitch-room     ← Stitch (Threads) 1:1 channel
├── #summit-room     ← Summit (LinkedIn) 1:1 channel
├── #pixel-room      ← Pixel (Instagram) 1:1 channel
└── #radar-room      ← Radar (News/Research) 1:1 channel
```

### The 5 Bots

| Bot | Role | SNS Platform | Action Code |
|-----|------|-------------|-------------|
| **Captain** (Team Lead) | Strategy, coordination, task delegation | X (Twitter) | `POST_X` |
| **Stitch** (Threads) | Short-form text content | Threads (Meta) | `POST_THREADS` |
| **Summit** (LinkedIn) | B2B / professional content | LinkedIn | `POST_LINKEDIN` |
| **Pixel** (Instagram) | Visual content (image required) | Instagram | `POST_INSTAGRAM` |
| **Radar** (News) | Market research, trend monitoring | X Search API | `SEARCH_NEWS` |

### How It Works

1. User or Captain gives a task in `#team-room` via @mention
2. The assigned bot generates content using AI (Claude / Codex)
3. Bot's response includes an `[ACTION:...]` block for SNS execution
4. Action engine parses the block and routes to the approval system
5. If `require_manual_approval=true`, the post queues for human review
6. Approved posts are published to the target platform

## Features

- **5-Bot Multi-Agent System** - Specialized bots collaborate via Discord @mentions
- **5 SNS Platforms** - X, Threads, LinkedIn, Instagram, News search
- **Action Engine** - LLM responses contain `[ACTION:TYPE]...[/ACTION]` blocks, parsed and executed automatically
- **Manual Approval** - Posts queue for human review before publishing (configurable)
- **Smart Memory** - Remembers past actions and avoids duplicate posts
- **Secrets Protection** - Pre-commit hooks and CI checks for sensitive data
- **Graceful Degradation** - Bots start even if some SNS credentials are missing

## Quick Start

### 1. Prerequisites

- Python 3.10+ (3.13 recommended)
- 5 Discord bot applications (one per bot)
- SNS API credentials for desired platforms

### 2. Install

```bash
git clone https://github.com/suojae/smol-marketing-claw.git
cd smol-marketing-claw
pip install -r requirements.txt
```

### 3. Environment Setup

Create a `.env` file in the project root:

```bash
# ── Discord Bot Tokens (one per bot) ──
DISCORD_LEAD_TOKEN=your_captain_bot_token
DISCORD_THREADS_TOKEN=your_stitch_bot_token
DISCORD_LINKEDIN_TOKEN=your_summit_bot_token
DISCORD_INSTAGRAM_TOKEN=your_pixel_bot_token
DISCORD_NEWS_TOKEN=your_radar_bot_token

# ── Discord Channel IDs ──
DISCORD_TEAM_CHANNEL_ID=123456789012345678    # #team-room
DISCORD_LEAD_CHANNEL_ID=123456789012345679    # #captain-room
DISCORD_THREADS_CHANNEL_ID=123456789012345680 # #stitch-room
DISCORD_LINKEDIN_CHANNEL_ID=123456789012345681 # #summit-room
DISCORD_INSTAGRAM_CHANNEL_ID=123456789012345682 # #pixel-room
DISCORD_NEWS_CHANNEL_ID=123456789012345683    # #radar-room

# ── X (Twitter) API Keys ──
X_CONSUMER_KEY=your_consumer_key
X_CONSUMER_SECRET=your_consumer_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret

# ── Threads (Meta) API ──
THREADS_USER_ID=your_threads_user_id
THREADS_ACCESS_TOKEN=your_threads_access_token

# ── LinkedIn API ──
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token

# ── Instagram (Meta Graph API) ──
INSTAGRAM_USER_ID=your_instagram_user_id
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token

# ── News (X Search API) ──
NEWS_X_BEARER_TOKEN=your_x_bearer_token

# ── AI Provider ──
AI_PROVIDER=claude                  # claude or codex
AI_DEFAULT_MODEL=sonnet             # opus, sonnet, or haiku

# ── Approval ──
REQUIRE_MANUAL_APPROVAL=true        # Set to false to auto-publish (not recommended)
```

### 4. Run

```bash
python autonomous-ai-server.py
```

The server starts and launches all Discord bots automatically. Bots with valid tokens will start; missing tokens are skipped with a log message.

## Discord Server Setup

### Creating Bot Applications

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create **5 applications** (Captain, Stitch, Summit, Pixel, Radar)
3. For each application:
   - Go to **Bot** tab > click **Reset Token** > copy and save the token
   - Enable **Message Content Intent** under Privileged Gateway Intents
   - Go to **OAuth2 > URL Generator**
   - Check `bot` scope
   - Check permissions: `Send Messages`, `Read Message History`, `View Channels`
   - Open the generated URL to invite the bot to your server

### Channel Structure

Create 6 text channels in your Discord server:

| Channel | Purpose |
|---------|---------|
| `#team-room` | All bots join. Collaboration via @mentions |
| `#captain-room` | 1:1 with Captain (Team Lead). User gives strategy directives |
| `#stitch-room` | 1:1 with Stitch. Threads content requests |
| `#summit-room` | 1:1 with Summit. LinkedIn content requests |
| `#pixel-room` | 1:1 with Pixel. Instagram content requests |
| `#radar-room` | 1:1 with Radar. News/trend research requests |

Right-click each channel > **Copy Channel ID** (requires Developer Mode) and add to `.env`.

## Action Engine

Bots communicate SNS actions via `[ACTION:TYPE]...[/ACTION]` blocks in their LLM responses.

### Action Format

```
[ACTION:POST_THREADS]
AI marketing is evolving fast. Here's what you need to know...
[/ACTION]
```

Instagram requires an `image_url:` field:
```
[ACTION:POST_INSTAGRAM]
Visual storytelling at its finest
image_url: https://example.com/image.jpg
[/ACTION]
```

News search:
```
[ACTION:SEARCH_NEWS]
AI marketing trends
[/ACTION]
```

### Security

- Action blocks in user messages are stripped (injection defense)
- Actions only execute in `#team-room` (not in 1:1 channels)
- Max 2 actions per message
- Empty action bodies are rejected
- Instagram `image_url` must be HTTPS
- News queries are sanitized (whitelist-based)
- All POST actions are audit-logged

## Approval System

When `REQUIRE_MANUAL_APPROVAL=true` (default), POST actions queue for human review instead of publishing immediately.

Use the web API to manage the queue:
- `GET /approvals/pending` - View pending posts
- `POST /approvals/{id}/approve` - Approve and publish a queued post
- `POST /approvals/{id}/reject` - Reject a queued post

## Configuration

Key settings in `src/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `ai_provider` | `claude` | AI backend (`claude` or `codex`) |
| `require_manual_approval` | `true` | Queue posts for human review |
| `usage_limits.max_calls_per_day` | `10000` | Daily API call limit |
| `autonomous_mode` | `true` | Enable autonomous operation |

## Secrets Protection

Pre-commit hooks and CI checks prevent accidental credential leaks.

```bash
# Install hooks
bash scripts/install-hooks.sh

# Manual check
python scripts/check-secrets.py --all
```

See `GUARDRAILS.md` for details.

## Requirements

- Python 3.10+
- Discord bot applications (up to 5)
- SNS API credentials (as needed per platform)
- Claude API key or Codex access (for AI features)

## License

MIT

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

Made by a human and Claude Code
