"""Domain layer — pure Python, no framework dependencies."""

from src.domain.models import ActionBlock
from src.domain.action_parser import parse_actions, strip_actions, escape_mentions
from src.domain.agent import AgentBrain
from src.domain.hr import resolve_bot, fire_bot, hire_bot, status_report

__all__ = [
    "ActionBlock",
    "AgentBrain",
    "parse_actions",
    "strip_actions",
    "escape_mentions",
    "resolve_bot",
    "fire_bot",
    "hire_bot",
    "status_report",
]
