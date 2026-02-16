"""News bot — market research, trend monitoring, competitor analysis."""

from typing import Optional

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import NEWS_PERSONA
from src.executor import AIExecutor


class NewsBot(BaseMarketingBot):
    """Market research and news monitoring bot.

    Responsibilities:
    - Industry trends and competitor analysis
    - Real-time news monitoring via X search
    - Insight reports for the team
    - Market trend briefings for team lead
    """

    def __init__(
        self,
        own_channel_id: int,
        team_channel_id: int,
        executor: Optional[AIExecutor] = None,
    ):
        super().__init__(
            bot_name="NewsBot",
            persona=NEWS_PERSONA,
            own_channel_id=own_channel_id,
            team_channel_id=team_channel_id,
            executor=executor,
        )
