---
name: setup
description: Guide through environment variable setup for Smol Claw
user_invocable: true
---

# /smol-claw:setup

Interactive setup guide for configuring Smol Claw environment variables.

## Required Environment Variables

### X (Twitter) API
- `X_CONSUMER_KEY` — Twitter API consumer key
- `X_CONSUMER_SECRET` — Twitter API consumer secret
- `X_ACCESS_TOKEN` — Twitter access token
- `X_ACCESS_TOKEN_SECRET` — Twitter access token secret

### Threads (Meta) API
- `THREADS_USER_ID` — Threads user ID
- `THREADS_ACCESS_TOKEN` — Threads access token

### Discord
- `DISCORD_BOT_TOKEN` — Discord bot token
- `DISCORD_CHANNEL_ID` — Target channel ID for notifications

### Optional
- `DISCORD_WEBHOOK_URL` — Webhook URL for notifications
- `AI_PROVIDER` — AI provider ("claude" or "codex", default: "claude")
- `AI_DEFAULT_MODEL` — Default model alias ("sonnet", "haiku", "opus")

## Steps

1. Check which environment variables are currently set
2. Call `smol_claw_status` to show current configuration state
3. Guide the user through setting up missing variables
4. Suggest adding them to a `.env` file in the project root
