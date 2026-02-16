"""Instagram bot — Instagram platform content creation and posting."""

from typing import Optional

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import INSTAGRAM_PERSONA
from src.executor import AIExecutor


class InstagramBot(BaseMarketingBot):
    """Instagram platform specialist bot.

    Responsibilities:
    - Instagram content planning and posting
    - Visual content strategy (images required)
    - Reels, Stories, Feed post planning
    """

    def __init__(
        self,
        own_channel_id: int,
        team_channel_id: int,
        executor: Optional[AIExecutor] = None,
    ):
        super().__init__(
            bot_name="InstagramBot",
            persona=INSTAGRAM_PERSONA,
            own_channel_id=own_channel_id,
            team_channel_id=team_channel_id,
            executor=executor,
        )
