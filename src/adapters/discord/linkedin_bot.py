"""LinkedIn bot — LinkedIn platform content creation and posting."""

from src.adapters.discord.base_bot import BaseMarketingBot
from src.domain.personas import LINKEDIN_PERSONA


class LinkedInBot(BaseMarketingBot):
    """LinkedIn platform specialist bot.

    Responsibilities:
    - LinkedIn content planning and posting
    - B2B marketing, thought leadership
    - Industry insights and professional networking content
    """

    def __init__(self, **kwargs):
        super().__init__(bot_name="LinkedInBot", persona=LINKEDIN_PERSONA, **kwargs)
