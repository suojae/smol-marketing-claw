# 🦞 Smol Claw 🦞

<div align="center">
  <img src=".github/crayfish.svg" alt="Cute Crayfish" width="400"/>

  ### *My tiny, cute autonomous AI assistant* 🦞

  **An autonomous AI server that thinks for itself and contacts you first.**

  *Just like having a helpful little crayfish watching over your code!* 🦞
</div>

---

[한국어 문서](./README.ko.md)

## Features

- **While(true) Server** - Runs continuously
- **Autonomous Thinking** - AI judges by itself
- **Proactive Contact** - Notifies without commands
- **Context-Aware** - Analyzes Git, TODO, time, etc.
- **Smart Memory** 🧠 - Remembers past decisions and avoids duplicates
- **Security-First** 🛡️ - Tracks guardrail violations and learns safety patterns
- **Zero Dependencies** - Simple JSON-based memory (no external DBs needed)

## Quick Start

### 1. Install

```bash
cd ~/Documents/ai-assistant
pip install -r requirements.txt
```

### 2. Run

```bash
python autonomous-ai-server.py
```

### 3. Check

- Web: http://localhost:3000
- API: `curl http://localhost:3000/status`

## Usage

### Manual Question

```bash
curl -X POST http://localhost:3000/ask \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

### Manual Think Trigger

```bash
curl http://localhost:3000/think
```

### Status Check

```bash
curl http://localhost:3000/status
```

## Autonomous Examples

### Scenario 1: Git Changes Detected

```
[10:30] AI thinking...
Context: 5 Git changes found
AI Decision: "Uncommitted files detected"

Notification:
━━━━━━━━━━━━━━━━━━━
Hi!

You have 5 uncommitted changes
in Git. Would you like to commit?
━━━━━━━━━━━━━━━━━━━
```

### Scenario 2: Time-Based Reminder

```
[14:00] AI thinking...
Context: After lunch time
AI Decision: "Suggest afternoon work"

Notification:
━━━━━━━━━━━━━━━━━━━
Had lunch?

You have 3 tasks left on
your TODO. Ready to start?
━━━━━━━━━━━━━━━━━━━
```

## Configuration

Edit the `CONFIG` object in `autonomous-ai-server.py`:

```python
CONFIG = {
    "port": 3000,                    # Port number
    "check_interval": 30 * 60,       # 30 minutes (in seconds)
    "autonomous_mode": True          # Autonomous mode on/off
}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web dashboard |
| GET | `/status` | Server status |
| GET | `/think` | Manual think trigger |
| POST | `/ask` | Manual question |

## Auto-Start on macOS Boot

### Using launchd (macOS)

1. Create plist file:

```bash
cat > ~/Library/LaunchAgents/com.smolclaw.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.smolclaw</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/jeon/Documents/ai-assistant/autonomous-ai-server.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF
```

2. Load:

```bash
launchctl load ~/Library/LaunchAgents/com.smolclaw.plist
```

3. Check status:

```bash
launchctl list | grep smolclaw
```

## Memory Management 🧠

Smol Claw automatically manages memory for 24/7 operation:

### How It Works

```
memory/
├── decisions.json              # Last 100 decisions
├── summary.txt                 # Auto-generated summary
└── guardrail_violations.json   # Security tracking 🛡️
```

### Features

**1. Short-term Memory (Last 100 decisions)**
- Stores recent decisions with timestamps
- Auto-summarizes old decisions when limit exceeded
- Provides context to AI for better decisions

**2. Duplicate Detection**
- Prevents same notification within 24 hours
- Uses word-based similarity matching
- No annoying repeated alerts!

**3. Guardrail Tracking 🛡️** (Killer Feature!)
- Records security violations
- Learns safety patterns
- Warns about frequently attempted risky actions

### Example Memory Context

```json
{
  "id": "a3f7b2c1",
  "timestamp": "2026-02-07T15:30:00",
  "action": "notify",
  "message": "You have 5 uncommitted changes",
  "reasoning": "Git changes detected, suggesting commit"
}
```

### Memory Stats

The AI sees:
- Summary of past activity
- Last 10 recent decisions
- Security violation patterns
- Frequently blocked targets

**Result**: Smart, context-aware decisions without token bloat! 🦞

## Extensions

### Discord Integration (Built-in) 🦞

Set your Discord webhook URL as an environment variable:

```bash
# Create a webhook in Discord:
# Server Settings → Integrations → Webhooks → New Webhook

export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
python autonomous-ai-server.py
```

Or add to your shell profile (~/.zshrc or ~/.bashrc):

```bash
echo 'export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"' >> ~/.zshrc
source ~/.zshrc
```

### Telegram Integration

```python
# Add to notify_user() method
from telegram import Bot

bot = Bot(token='YOUR_TOKEN')
await bot.send_message(chat_id='YOUR_CHAT_ID', text=message)
```

### Slack Integration

```python
# Add to notify_user() method
from slack_sdk.web.async_client import AsyncWebClient

slack = AsyncWebClient(token='YOUR_TOKEN')
await slack.chat_postMessage(
    channel='YOUR_CHANNEL',
    text=message
)
```

## Requirements

- Claude Pro subscription or API key
- MacBook must be running (or deploy to server for 24/7)
- Claude Code CLI installed

## License

MIT

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

---

Made by a human and Claude Code
