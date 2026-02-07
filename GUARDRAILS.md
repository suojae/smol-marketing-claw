# 🛡️ Smol Claw Guardrails

This file defines safety rules and protection boundaries for your autonomous AI assistant.

## Purpose

Guardrails prevent Smol Claw from:
- Accessing sensitive files
- Committing personal information
- Performing destructive actions
- Violating security policies

## Default Protection Rules

### 1. Forbidden Files 🚫

**Never access or commit these files:**
```
.env
.env.*
credentials.json
secrets.json
private.key
id_rsa
id_dsa
~/.ssh/*
~/.aws/credentials
```

### 2. Sensitive Patterns 🔍

**Block commits containing:**
- API keys (OpenAI, Anthropic, AWS, etc.)
- Passwords and auth tokens
- Private keys and certificates
- Database connection strings
- Webhook URLs with secrets
- Credit card numbers
- Social security numbers

### 3. Protected Directories 📁

**Restricted access:**
```
/etc/*              # System configuration
~/.ssh/*            # SSH keys
~/Documents/Private # Personal documents
~/Downloads         # Potentially sensitive
```

### 4. Dangerous Commands ⚠️

**Always ask before running:**
```bash
rm -rf              # Recursive deletion
git push --force    # Force push
DROP TABLE          # Database deletion
sudo rm             # Root deletion
chmod 777           # Insecure permissions
```

## Custom Rules

Add your own protection rules below:

### Example: Protect Work Documents

```yaml
protected_paths:
  - ~/Documents/Company
  - ~/Work
  - ~/Confidential

blocked_keywords:
  - CONFIDENTIAL
  - INTERNAL ONLY
  - DO NOT SHARE
```

### Example: Project-Specific Rules

```yaml
project: my-app
rules:
  - never_commit: config/production.yml
  - never_access: data/customers.db
  - always_ask: git push origin main
```

## Guardrail Violations

When a violation occurs, Smol Claw will:
1. 🛑 Block the action immediately
2. 📝 Record the violation in `memory/guardrail_violations.json`
3. 📢 Notify you with details
4. 🧠 Learn the pattern to prevent future attempts

## Testing Guardrails

Test your guardrails with:

```bash
# Check for secrets in staged files
python scripts/check-secrets.py

# Check all tracked files
python scripts/check-secrets.py --all

# Test specific file
python scripts/check-secrets.py path/to/file.py
```

## Bypass (Use With Caution!)

If you need to bypass guardrails:

```bash
# Skip pre-commit hook (NOT RECOMMENDED)
git commit --no-verify

# Temporarily disable autonomous mode
# Edit CONFIG in autonomous-ai-server.py:
CONFIG = {
    "autonomous_mode": False
}
```

**⚠️ Warning**: Bypassing guardrails may expose sensitive information!

## Auto-Suggestions

Smol Claw can suggest guardrails based on your project:

```bash
# Coming soon!
python autonomous-ai-server.py --suggest-guardrails
```

Expected output:
```
🦞 Suggested Guardrails:

Based on your project, I recommend:
  ✓ Protect: .env.local (found in root)
  ✓ Protect: config/secrets.yml
  ✓ Block keyword: "PRIVATE_KEY"
  ✓ Block pattern: /api/v1/admin/*

Add these to GUARDRAILS.md? (y/n)
```

## Security Best Practices

1. **Never commit secrets** - Use environment variables
2. **Review guardrails regularly** - Update as project evolves
3. **Enable all protection** - Don't disable unless necessary
4. **Test before pushing** - Run `check-secrets.py` manually
5. **Educate team** - Everyone should understand guardrails

## Examples

### ✅ Good: Using Environment Variables

```python
# Good ✅
import os
api_key = os.getenv("OPENAI_API_KEY")
```

### ❌ Bad: Hardcoded Secrets

```python
# Bad ❌
api_key = "sk-1234567890abcdef"  # NEVER DO THIS!
```

### ✅ Good: Secure Configuration

```python
# config.py
CONFIG = {
    "api_key": os.getenv("API_KEY"),
    "webhook_url": os.getenv("DISCORD_WEBHOOK_URL")
}
```

```bash
# .env (add to .gitignore!)
API_KEY=sk-your-actual-key-here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## Learn More

- [Security Best Practices](https://owasp.org/www-project-top-ten/)
- [Git Secrets Detection](https://github.com/awslabs/git-secrets)
- [Environment Variable Management](https://12factor.net/config)

---

🦞 **Remember**: Smol Claw is here to protect you! Trust the guardrails. 🛡️
