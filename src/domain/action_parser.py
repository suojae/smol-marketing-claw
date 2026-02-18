"""Action block parsing — extracted from base_bot.py.

Pure Python, no framework dependencies.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Dict, List, Tuple

from src.domain.models import ActionBlock

if TYPE_CHECKING:
    from src.domain.alarm import AlarmEntry

# Action block regex: [ACTION:TYPE] ... [/ACTION]
ACTION_RE = re.compile(
    r"\[ACTION:(\w+)\]\s*(.*?)\s*\[/ACTION\]",
    re.DOTALL,
)

# Map ACTION codes -> (platform, action_kind)
ACTION_MAP: Dict[str, Tuple[str, str]] = {
    "POST_THREADS": ("threads", "post"),
    "POST_LINKEDIN": ("linkedin", "post"),
    "POST_INSTAGRAM": ("instagram", "post"),
    "POST_X": ("x", "post"),
    "SEARCH_NEWS": ("news", "search"),
    "SET_ALARM": ("alarm", "set"),
    "CANCEL_ALARM": ("alarm", "cancel"),
}

# Max actions per single LLM response (spam prevention)
MAX_ACTIONS_PER_MESSAGE = 2


def parse_actions(text: str) -> List[ActionBlock]:
    """Extract action blocks from LLM response text."""
    return [
        ActionBlock(action_type=action_type, body=body.strip())
        for action_type, body in ACTION_RE.findall(text)
    ]


def strip_actions(text: str) -> str:
    """Remove all action blocks from text."""
    return ACTION_RE.sub("", text).strip()


def escape_mentions(text: str) -> str:
    """Escape @mentions to prevent triggering other bots."""
    return re.sub(r"@(\w+)", r"`@\1`", text)


def parse_alarm_body(body: str) -> Dict[str, str]:
    """Parse key: value lines from action body.

    Lines without a colon are appended to the previous key's value,
    supporting multiline prompt fields.
    """
    fields: Dict[str, str] = {}
    last_key = None
    for line in body.strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            fields[key] = value.strip()
            last_key = key
        elif last_key is not None:
            fields[last_key] += "\n" + line
    return fields


def parse_instagram_body(body: str) -> Tuple[str, str]:
    """Parse Instagram action body to extract caption and image_url."""
    lines = body.strip().splitlines()
    image_url = ""
    caption_lines = []
    for line in lines:
        if line.strip().lower().startswith("image_url:"):
            image_url = line.split(":", 1)[1].strip()
        else:
            caption_lines.append(line)
    return "\n".join(caption_lines).strip(), image_url


def format_schedule(alarm: "AlarmEntry") -> str:
    """Format alarm schedule for display."""
    if alarm.schedule_type == "daily":
        return f"매일 {alarm.hour:02d}:{alarm.minute:02d}"
    elif alarm.schedule_type == "weekday":
        return f"평일 {alarm.hour:02d}:{alarm.minute:02d}"
    elif alarm.schedule_type == "interval":
        if alarm.interval_minutes >= 60 and alarm.interval_minutes % 60 == 0:
            return f"{alarm.interval_minutes // 60}시간마다"
        return f"{alarm.interval_minutes}분마다"
    elif alarm.schedule_type == "once":
        if alarm.interval_minutes >= 60 and alarm.interval_minutes % 60 == 0:
            return f"{alarm.interval_minutes // 60}시간 후 1회"
        return f"{alarm.interval_minutes}분 후 1회"
    return alarm.schedule_type
