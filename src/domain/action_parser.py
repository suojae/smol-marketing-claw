"""Action block parsing — extracted from base_bot.py.

Pure Python, no framework dependencies.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from src.domain.models import ActionBlock

# Action block regex: [ACTION:TYPE] ... [/ACTION]
ACTION_RE = re.compile(
    r"\[ACTION:(\w+)\]\s*(.*?)\s*\[/ACTION\]",
    re.DOTALL,
)

# Map ACTION codes -> (platform, action_kind)
ACTION_MAP: Dict[str, Tuple[str, str]] = {
    "POST_THREADS": ("threads", "post"),
    "POST_INSTAGRAM": ("instagram", "post"),
    "POST_X": ("x", "post"),
    "FIRE_BOT": ("hr", "fire"),
    "HIRE_BOT": ("hr", "hire"),
    "STATUS_REPORT": ("hr", "status"),
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
