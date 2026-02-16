---
name: hormone-nudge
description: Manually adjust hormone levels (dopamine, cortisol)
user_invocable: true
---

# /smol-claw:hormone-nudge

Manually adjust hormone levels to influence AI behavior.

## Arguments

- First argument: dopamine delta (-0.3 to 0.3)
- Second argument: cortisol delta (-0.3 to 0.3)

Example: `/smol-claw:hormone-nudge 0.2 -0.1` boosts dopamine by 0.2 and reduces cortisol by 0.1.

## Steps

1. Parse the arguments as dopamine_delta and cortisol_delta
2. Call the `smol_claw_hormone_nudge` MCP tool with the parsed values
3. Display the updated hormone state
