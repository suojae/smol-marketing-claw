"""Researcher bot — market research, trend monitoring, competitor analysis."""

from src.adapters.discord.base_bot import BaseMarketingBot
from src.domain.personas import NEWS_PERSONA


class ResearcherBot(BaseMarketingBot):
    """Market research and news monitoring bot.

    Responsibilities:
    - Industry trends and competitor analysis
    - Real-time news monitoring via X search
    - Insight reports for the team
    - Market trend briefings for team lead
    """

    def __init__(self, **kwargs):
        super().__init__(
            bot_name="ResearcherBot",
            persona=NEWS_PERSONA,
            aliases=["NewsBot"],
            **kwargs,
        )
