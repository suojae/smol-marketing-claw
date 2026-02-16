---
name: status
description: Show current Smol Claw system status (hormones, usage, SNS config)
user_invocable: true
---

# /smol-claw:status

Display the full system status including hormone levels, usage statistics, and SNS configuration.

## Steps

1. Call the `smol_claw_status` MCP tool
2. Format the results in a readable way:
   - Hormone state: dopamine, cortisol, energy, label
   - Usage: calls today/hour/minute, limits
   - SNS: X and Threads configuration status
   - Discord: bot status
