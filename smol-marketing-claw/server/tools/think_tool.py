"""MCP tool for autonomous think cycle."""

import sys
from typing import Optional

from server.mcp_server import mcp
from server.state import get_state
from src.domain.persona import BOT_PERSONA


def _log(msg: str):
    print(msg, file=sys.stderr)


def _build_system_prompt() -> str:
    """Build system prompt for autonomous thinking."""
    return BOT_PERSONA + """

You are also an autonomous AI assistant.

Role:
- Judge and act autonomously without user commands
- Analyze provided context to decide necessary actions
- Proactively contact and suggest

Decision criteria:
1. Git changes -> suggest commit
2. TODOs exist -> check progress
3. Important time -> remind
4. Abandoned tasks -> notify

Response format:
- action: "none" | "notify" | "suggest" | "remind"
- message: message to user
- reasoning: why this action was taken

Respond in JSON format."""


@mcp.tool()
async def smol_claw_think(events: Optional[str] = None) -> dict:
    """Run one autonomous think cycle.

    Collects context, builds a prompt, and returns the prompt + context
    for Claude to process directly.

    Args:
        events: Optional newline-separated event descriptions (e.g. "file_changed: src/app.py").
    """
    state = get_state()

    _log("Smol Claw thinking...")

    # Collect context
    context = await state.context_collector.collect()

    # Build git status string
    git_status = "none"
    if context["git"]:
        git_status = f"branch {context['git']['branch']}, "
        git_status += "has changes" if context["git"]["hasChanges"] else "no changes"

    # Build event summary
    event_text = ""
    if events:
        event_lines = "\n".join([f"- {e.strip()}" for e in events.strip().split("\n") if e.strip()])
        event_text = f"\nDetected events:\n{event_lines}\n"

    # Memory context
    memory_context = state.memory.get_context()
    safety_context = state.memory.get_safety_context()

    # Build the prompt
    prompt = f"""Current situation:

Time: {context['time']}
Git status: {git_status}
TODOs: {len(context['tasks'])}
{event_text}
{memory_context}
{safety_context}

Based on your judgment:
1. Is there anything to notify the user about?
2. Any suggestions?
3. Any reminders?

Check recent activity and avoid duplicate notifications.

Respond in JSON with keys: action, message, reasoning."""

    system_prompt = _build_system_prompt()

    return {
        "system_prompt": system_prompt,
        "prompt": prompt,
        "context_summary": {
            "time": context["time"],
            "git_status": git_status,
            "todo_count": len(context["tasks"]),
            "events": event_text.strip() or None,
        },
        "instructions": (
            "Process the prompt above using the system_prompt as your persona. "
            "Return a JSON decision with action/message/reasoning. "
            "After deciding, call smol_claw_record_outcome with the result."
        ),
    }


@mcp.tool()
async def smol_claw_record_outcome(
    action: str = "none",
    message: str = "",
    reasoning: str = "",
) -> dict:
    """Record the outcome of a think cycle into memory.

    Call this after processing the think prompt to persist the decision.

    Args:
        action: The decided action ("none", "notify", "suggest", "remind").
        message: The message to the user.
        reasoning: Why this action was taken.
    """
    state = get_state()

    decision = {
        "action": action,
        "message": message,
        "reasoning": reasoning,
    }

    # Check for duplicates
    if action != "none" and message:
        if state.memory.should_skip_duplicate(message):
            _log("Skipping duplicate notification")
            decision["action"] = "skipped"
            decision["reasoning"] = "Duplicate notification (sent within 24h)"
            state.memory.add_decision(decision)
            return {"recorded": True, "decision": decision}

    # Save decision to memory
    state.memory.add_decision(decision)

    return {"recorded": True, "decision": decision}
