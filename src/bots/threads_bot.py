"""Threads bot — Threads platform content creation and posting."""

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import THREADS_PERSONA


class ThreadsBot(BaseMarketingBot):
    """Threads platform specialist bot.

    Responsibilities:
    - Threads content planning and posting
    - Trend analysis, hashtag strategy
    - Short, impactful text content
    """

    def __init__(self, **kwargs):
        super().__init__(bot_name="ThreadsBot", persona=THREADS_PERSONA, **kwargs)
