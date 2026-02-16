"""Team Lead bot — strategy, coordination, sub-bot management."""

from typing import Any, Dict, Optional

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import TEAM_LEAD_PERSONA
from src.executor import AIExecutor


class TeamLeadBot(BaseMarketingBot):
    """Marketing team leader bot.

    Responsibilities:
    - Overall marketing strategy
    - Coordinate sub-bots via @mentions in #team-room
    - Campaign planning and performance analysis
    """

    def __init__(
        self,
        own_channel_id: int,
        team_channel_id: int,
        executor: Optional[AIExecutor] = None,
        clients: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            bot_name="TeamLead",
            persona=TEAM_LEAD_PERSONA,
            own_channel_id=own_channel_id,
            team_channel_id=team_channel_id,
            executor=executor,
            clients=clients,
        )
