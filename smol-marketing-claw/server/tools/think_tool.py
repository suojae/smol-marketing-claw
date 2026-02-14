"""MCP tool for autonomous think cycle."""

import json
import sys
from datetime import datetime
from typing import Optional, List

from server.mcp_server import mcp
from server.state import get_state
from src.persona import BOT_PERSONA
from src.hormone_memory import HormoneEpisode


POSITIVE_KEYWORDS = frozenset([
    "success", "engagement", "liked", "popular", "growth", "completed",
])
NEGATIVE_KEYWORDS = frozenset([
    "error", "fail", "blocked", "rejected", "timeout", "crash",
])


def _log(msg: str):
    print(msg, file=sys.stderr)


def _build_system_prompt(state) -> str:
    """Build system prompt for autonomous thinking."""
    base = BOT_PERSONA + """

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

    if state.hormones:
        params = state.hormones.get_control_params()
        base += f"\n\n{params.persona_modifier}"

    return base


@mcp.tool()
async def smol_claw_think(events: Optional[str] = None) -> dict:
    """Run one autonomous think cycle.

    Collects context, builds a prompt with hormone state and past experience,
    and returns the prompt + context for Claude to process directly.
    Claude IS the LLM — no subprocess call needed.

    Args:
        events: Optional newline-separated event descriptions (e.g. "file_changed: src/app.py").
    """
    state = get_state()
    state.reload_hormones_if_stale()

    _log("Smol Claw thinking...")

    # Hormone decay at start of think cycle
    if state.hormones:
        state.hormones.decay()

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

    # Retrieve past similar experience from vector DB
    experience_context = ""
    if state.hormone_memory and state.hormone_memory.enabled and state.hormones:
        label = state.hormones._label_state()
        event_summary = event_text.strip() or "routine check"
        experience_context = state.hormone_memory.get_experience_context(
            f"감정:{label} 이벤트:{event_summary}"
        )
        if experience_context:
            experience_context = "\n" + experience_context + "\n"

    # Build the prompt
    prompt = f"""Current situation:

Time: {context['time']}
Git status: {git_status}
TODOs: {len(context['tasks'])}
{event_text}
{memory_context}
{experience_context}
{safety_context}

Based on your judgment:
1. Is there anything to notify the user about?
2. Any suggestions?
3. Any reminders?

Check recent activity and avoid duplicate notifications.

Respond in JSON with keys: action, message, reasoning."""

    system_prompt = _build_system_prompt(state)

    # Hormone status for the caller
    hormone_status = state.hormones.get_status_dict() if state.hormones else None

    # Save hormone state
    if state.hormones:
        state.hormones.save_state()

    return {
        "system_prompt": system_prompt,
        "prompt": prompt,
        "context_summary": {
            "time": context["time"],
            "git_status": git_status,
            "todo_count": len(context["tasks"]),
            "events": event_text.strip() or None,
        },
        "hormone_state": hormone_status,
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
    """Record the outcome of a think cycle into memory and hormones.

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

    # Check for duplicates first (before hormone update to avoid rewarding duplicates)
    if action != "none" and message:
        if state.memory.should_skip_duplicate(message):
            _log("Skipping duplicate notification")
            decision["action"] = "skipped"
            decision["reasoning"] = "Duplicate notification (sent within 24h)"
            if state.hormones:
                state.hormones.trigger_cortisol(0.05)
            state.memory.add_decision(decision)
            if state.hormones:
                state.hormones.save_state()
            return {
                "recorded": True,
                "decision": decision,
                "hormone_state": state.hormones.get_status_dict() if state.hormones else None,
            }

    # Update hormones from decision (only for non-duplicate decisions)
    if state.hormones:
        text = json.dumps(decision, ensure_ascii=False).lower()

        for kw in POSITIVE_KEYWORDS:
            if kw in text:
                state.hormones.trigger_dopamine(0.1)
                break

        if action in ("notify", "suggest", "remind"):
            state.hormones.trigger_dopamine(0.05)

        for kw in NEGATIVE_KEYWORDS:
            if kw in text:
                state.hormones.trigger_cortisol(0.15)
                break

    # Save decision to memory
    state.memory.add_decision(decision)

    # Record episode to vector DB
    if state.hormone_memory and state.hormone_memory.enabled and state.hormones:
        episode = HormoneEpisode(
            timestamp=datetime.now().isoformat(),
            dopamine=state.hormones.state.dopamine,
            cortisol=state.hormones.state.cortisol,
            energy=state.hormones.state.energy,
            emotional_state=state.hormones._label_state(),
            events=reasoning or "think cycle",
            decision_action=action,
            decision_message=message,
            outcome_summary=reasoning,
        )
        state.hormone_memory.record_episode(episode)

    # Save hormone state
    if state.hormones:
        state.hormones.save_state()

    return {
        "recorded": True,
        "decision": decision,
        "hormone_state": state.hormones.get_status_dict() if state.hormones else None,
    }
