"""HR Bot — agent fire/hire/status management.

Core HR functions are in src.domain.hr. This module re-exports them
for backward compatibility and provides the HRBot Discord adapter.
"""

from typing import Dict

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import HR_PERSONA
from src.domain.hr import (
    BOT_NAME_ALIASES,
    HISTORY_FIRE_THRESHOLD,
    HISTORY_WARN_THRESHOLD,
    PROTECTED_KEYS,
    fire_bot,
    hire_bot,
    resolve_bot,
    status_report,
)

# Re-export domain functions for backward compatibility
__all__ = [
    "BOT_NAME_ALIASES",
    "PROTECTED_KEYS",
    "HISTORY_WARN_THRESHOLD",
    "HISTORY_FIRE_THRESHOLD",
    "resolve_bot",
    "fire_bot",
    "hire_bot",
    "status_report",
    "HRBot",
]


class HRBot(BaseMarketingBot):
    """Human Resources bot for managing agent lifecycle.

    Actions:
    - FIRE_BOT: Deactivate a bot and clear its conversation history
    - HIRE_BOT: Reactivate a previously fired bot
    - STATUS_REPORT: Show status of all registered bots
    """

    def __init__(self, bot_registry=None, **kwargs):
        kwargs.pop("clients", None)  # HR has no SNS clients
        super().__init__(bot_name="HRBot", persona=HR_PERSONA, aliases=["HR"], **kwargs)
        self.bot_registry: Dict[str, BaseMarketingBot] = bot_registry or {}

    async def _execute_action(self, action_type: str, body: str, message=None) -> str:
        """Handle HR-specific actions, delegate others to base."""
        if action_type == "FIRE_BOT":
            return await fire_bot(body.strip(), self.bot_registry, self.bot_name)
        elif action_type == "HIRE_BOT":
            return await hire_bot(body.strip(), self.bot_registry, self.bot_name)
        elif action_type == "STATUS_REPORT":
            return status_report(self.bot_registry, self.bot_name)
        return await super()._execute_action(action_type, body, message=message)
