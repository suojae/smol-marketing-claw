"""Team Lead bot — strategy, coordination, sub-bot management."""

from typing import Dict

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import TEAM_LEAD_PERSONA


class TeamLeadBot(BaseMarketingBot):
    """Marketing team leader bot.

    Responsibilities:
    - Overall marketing strategy
    - Coordinate sub-bots via @mentions in #team-room
    - Campaign planning and performance analysis
    - Fire/hire team members to optimize context quality
    """

    def __init__(self, bot_registry=None, **kwargs):
        super().__init__(bot_name="TeamLead", persona=TEAM_LEAD_PERSONA, **kwargs)
        self.bot_registry: Dict[str, BaseMarketingBot] = bot_registry or {}

    async def _execute_action(self, action_type: str, body: str) -> str:
        """Handle HR actions (fire/hire/status) in addition to SNS actions."""
        if action_type in ("FIRE_BOT", "HIRE_BOT", "STATUS_REPORT"):
            from src.bots.hr_bot import fire_bot, hire_bot, status_report
            if action_type == "FIRE_BOT":
                return await fire_bot(body.strip(), self.bot_registry, self.bot_name)
            elif action_type == "HIRE_BOT":
                return await hire_bot(body.strip(), self.bot_registry, self.bot_name)
            else:
                return status_report(self.bot_registry, self.bot_name)
        return await super()._execute_action(action_type, body)
