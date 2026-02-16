---
name: discord
description: Control the Discord bot (start/stop/status)
user_invocable: true
---

# /smol-claw:discord

Control the Discord bot integration.

## Arguments

- First argument: action ("start", "stop", or "status")

Example: `/smol-claw:discord start`

## Steps

1. Parse the argument as the action
2. Call the `smol_claw_discord_control` MCP tool with the action
3. Display the result
