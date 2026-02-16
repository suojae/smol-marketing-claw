---
name: think
description: Run one autonomous think cycle — analyze context and make a decision
user_invocable: true
---

# /smol-claw:think

Run one autonomous thinking cycle. Collects context (git, TODOs, time), considers hormone state and past experience, then makes a decision.

## Steps

1. Call the `smol_claw_think` MCP tool (optionally with events)
2. Read the returned `system_prompt` and `prompt`
3. Process the prompt as instructed — act as the Smol Claw persona
4. Decide on an action: "none", "notify", "suggest", or "remind"
5. Call `smol_claw_record_outcome` with your decision (action, message, reasoning)
6. Display the decision to the user
