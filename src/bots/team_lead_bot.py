"""Team Lead bot — strategy, coordination, sub-bot management."""

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import TEAM_LEAD_PERSONA


class TeamLeadBot(BaseMarketingBot):
    """Marketing team leader bot.

    Responsibilities:
    - Overall marketing strategy
    - Coordinate sub-bots via @mentions in #team-room
    - Campaign planning and performance analysis
    """

    def __init__(self, **kwargs):
        super().__init__(bot_name="TeamLead", persona=TEAM_LEAD_PERSONA, **kwargs)
