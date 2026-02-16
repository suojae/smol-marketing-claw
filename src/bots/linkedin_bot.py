"""LinkedIn bot — LinkedIn platform content creation and posting."""

from typing import Optional

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import LINKEDIN_PERSONA
from src.executor import AIExecutor


class LinkedInBot(BaseMarketingBot):
    """LinkedIn platform specialist bot.

    Responsibilities:
    - LinkedIn content planning and posting
    - B2B marketing, thought leadership
    - Industry insights and professional networking content
    """

    def __init__(
        self,
        own_channel_id: int,
        team_channel_id: int,
        executor: Optional[AIExecutor] = None,
    ):
        super().__init__(
            bot_name="LinkedInBot",
            persona=LINKEDIN_PERSONA,
            own_channel_id=own_channel_id,
            team_channel_id=team_channel_id,
            executor=executor,
        )
