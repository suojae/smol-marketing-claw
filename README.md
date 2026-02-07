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
- **Secrets Protection** 🛡️ - Prevents committing API keys, passwords, .env files
- **Safe by Default** - Pre-commit hooks and CI checks for sensitive data

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

## Secrets Protection 🛡️

Smol Claw protects you from accidentally committing sensitive information!

### What's Protected

Automatically detects and blocks:
- 🔑 API keys (OpenAI, Anthropic, AWS, etc.)
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

### Example: Blocked Commit

```bash
$ git commit -m "add config"
🦞 Checking for sensitive information...

======================================================================
🛡️  SECURITY ALERT: Sensitive Information Detected! 🛡️
======================================================================

❌ API Key detected!
   File: config.py:5
   Line: api_key=[REDACTED]

❌ Forbidden file!
   File: .env

======================================================================
🦞 Smol Claw prevented you from committing sensitive data!

What to do:
  1. Remove sensitive information from the files
  2. Use environment variables instead: os.getenv('API_KEY')
  3. Add sensitive files to .gitignore
  4. Update GUARDRAILS.md with protection rules
======================================================================

# Commit blocked! ✅
```

### Best Practices

**✅ Good: Use Environment Variables**
```python
import os

# Store in .env (add to .gitignore!)
api_key = os.getenv("OPENAI_API_KEY")
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
```

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

**❌ Bad: Hardcode Secrets**
```python
# NEVER DO THIS! ❌
api_key = "sk-1234567890abcdef"
password = "mypassword123"
```

### Guardrails

See `GUARDRAILS.md` for:
- Complete protection rules
- Custom guardrail configuration
- Testing and bypass options
- Security best practices

🦞 **Your secrets are safe with Smol Claw!** 🛡️

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
