# 🦞 Smol Marketing Claw 🦞

<div align="center">
  <img src=".github/crayfish.svg" alt="Cute Crayfish" width="400"/>

  ### *Your tiny, cute AI marketing assistant* 🦞

  **An AI-powered SNS marketing plugin that posts, replies, and notifies for you.**

  *Just like having a helpful little crayfish managing your social media!* 🦞
</div>

---

[한국어 문서](./README.ko.md)

## Features

- **X (Twitter) Integration** - Post tweets & reply to conversations
- **Threads (Meta) Integration** - Publish posts & reply on Threads
- **Discord Notifications** - Real-time marketing alerts via Discord
- **Smart Memory** 🧠 - Remembers past actions and avoids duplicate posts
- **Secrets Protection** 🔒 - Prevents leaking API keys, tokens, and credentials
- **Safe by Default** - Pre-commit hooks and CI checks for sensitive data
- **Claude AI Powered** - Intelligent content decisions via Anthropic Claude
- **Zero Dependencies** - Simple JSON-based memory (no external DBs needed)

## Quick Start

### 1. Environment Setup

Create a `.env` file in the project root:

```bash
# X (Twitter) API Keys — required for X integration
X_CONSUMER_KEY=your_consumer_key
X_CONSUMER_SECRET=your_consumer_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret

# Threads (Meta) API — required for Threads integration
THREADS_USER_ID=your_threads_user_id
THREADS_ACCESS_TOKEN=your_threads_access_token

# Discord (optional — for notifications)
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CHANNEL_ID=your_channel_id
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 2. Install

```bash
git clone https://github.com/suojae/smol-claw.git
cd smol-claw
pip install -r requirements.txt
```

### 3. Run

```bash
python autonomous-ai-server.py
```

### 4. Check

- Web: http://localhost:3000
- API: `curl http://localhost:3000/status`

## Usage Examples

### Post a Tweet

```bash
curl -X POST http://localhost:3000/sns/x/post \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Smol Marketing Claw! 🦞"}'
```

### Reply to a Tweet

```bash
curl -X POST http://localhost:3000/sns/x/reply \
  -H "Content-Type: application/json" \
  -d '{"text": "Thanks for the feedback!", "post_id": "1234567890"}'
```

### Post to Threads

```bash
curl -X POST http://localhost:3000/sns/threads/post \
  -H "Content-Type: application/json" \
  -d '{"text": "New product launch coming soon! 🦞"}'
```

### Reply on Threads

```bash
curl -X POST http://localhost:3000/sns/threads/reply \
  -H "Content-Type: application/json" \
  -d '{"text": "Great question — check our link in bio!", "post_id": "9876543210"}'
```

### Check Server Status

```bash
curl http://localhost:3000/status
```

### Ask Claude a Question

```bash
curl -X POST http://localhost:3000/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "Draft a tweet about our new feature"}'
```

## Marketing Scenarios

### Scenario 1: Product Launch Tweet

```bash
# Post announcement on X
curl -X POST http://localhost:3000/sns/x/post \
  -d '{"text": "We just launched our new dashboard! Check it out at example.com 🚀"}' \
  -H "Content-Type: application/json"

# Cross-post to Threads
curl -X POST http://localhost:3000/sns/threads/post \
  -d '{"text": "We just launched our new dashboard! Check it out at example.com 🚀"}' \
  -H "Content-Type: application/json"
```

### Scenario 2: Community Engagement

```bash
# Reply to customer feedback on X
curl -X POST http://localhost:3000/sns/x/reply \
  -d '{"text": "Thank you for the kind words! We appreciate your support 🦞", "post_id": "1234567890"}' \
  -H "Content-Type: application/json"
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web dashboard |
| GET | `/status` | Server status & usage info |
| POST | `/ask` | Ask Claude a question |
| POST | `/sns/x/post` | Post a tweet to X (Twitter) |
| POST | `/sns/x/reply` | Reply to a tweet on X |
| POST | `/sns/threads/post` | Post to Threads (Meta) |
| POST | `/sns/threads/reply` | Reply to a post on Threads |

### SNS Request/Response Format

**Post Request Body:**
```json
{ "text": "Your post content here" }
```

**Reply Request Body:**
```json
{ "text": "Your reply content", "post_id": "target_post_id" }
```

**Response:**
```json
{
  "success": true,
  "post_id": "1234567890",
  "text": "Your post content here"
}
```

**Text Limits:**
- X (Twitter): 280 characters (auto-truncated)
- Threads (Meta): 500 characters (auto-truncated)

## Configuration

Edit environment variables or the `CONFIG` object in `src/config.py`:

```python
CONFIG = {
    "port": 3000,                    # Port number
    "check_interval": 30 * 60,       # 30 minutes (in seconds)
    "autonomous_mode": True          # Autonomous mode on/off
}
```

## Secrets Protection 🛡️

Smol Marketing Claw protects you from accidentally leaking sensitive marketing API credentials!

### What's Protected

Automatically detects and blocks:
- 🔑 API keys (X Consumer Key, Threads Access Token, etc.)
- 🔐 Passwords and auth tokens
- 🔒 Private keys and certificates
- 💳 Database connection strings
- 🪝 Webhook URLs with secrets
- 📄 .env files and credentials

### How It Works

**1. Pre-commit Hook** (Local Protection)
```bash
# Install hooks (done automatically by quickstart.sh)
bash scripts/install-hooks.sh

# Now git will check before every commit!
git commit -m "add feature"
# 🦞 Checking for sensitive information...
# ✅ No sensitive information detected! Safe to commit. 🦞
```

**2. CI/CD Check** (Remote Protection)
```yaml
# Runs automatically on every push/PR
- name: Check for secrets 🛡️
  run: python3 scripts/check-secrets.py --all
```

**3. Manual Check**
```bash
# Check staged files
python scripts/check-secrets.py

# Check all tracked files
python scripts/check-secrets.py --all

# Check specific file
python scripts/check-secrets.py config.py
```

### Best Practices

**✅ Good: Use Environment Variables**
```python
import os

# Store in .env (add to .gitignore!)
x_key = os.getenv("X_CONSUMER_KEY")
threads_token = os.getenv("THREADS_ACCESS_TOKEN")
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
```

**❌ Bad: Hardcode Secrets**
```python
# NEVER DO THIS! ❌
x_key = "ck-1234567890abcdef"
threads_token = "IGQ..."
```

### Guardrails

See `GUARDRAILS.md` for:
- Complete protection rules
- Custom guardrail configuration
- Testing and bypass options
- Security best practices

🦞 **Your API keys are safe with Smol Marketing Claw!** 🛡️

## Discord Setup

1. Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. Enable **Message Content Intent** under Bot settings
3. Invite the bot to your server with `Send Messages` permission
4. Add credentials to your `.env` file:

```bash
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CHANNEL_ID=your_channel_id
```

5. Get the channel ID: Discord Settings > Advanced > Developer Mode > Right-click channel > Copy Channel ID

## Requirements

- Python 3.9+
- X (Twitter) Developer Account (for X integration)
- Threads/Meta Developer Account (for Threads integration)
- Discord Bot (optional, for notifications)
- Claude Pro subscription or API key (for AI features)

## License

MIT

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

Made by a human and Claude Code 🦞
