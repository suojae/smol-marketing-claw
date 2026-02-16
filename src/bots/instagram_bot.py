"""Instagram bot — Instagram platform content creation and posting."""

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import INSTAGRAM_PERSONA


class InstagramBot(BaseMarketingBot):
    """Instagram platform specialist bot.

    Responsibilities:
    - Instagram content planning and posting
    - Visual content strategy (images required)
    - Reels, Stories, Feed post planning
    """

    def __init__(self, **kwargs):
        super().__init__(bot_name="InstagramBot", persona=INSTAGRAM_PERSONA, **kwargs)
