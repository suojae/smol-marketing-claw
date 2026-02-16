"""Threads bot — Threads platform content creation and posting."""

from typing import Optional

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import THREADS_PERSONA
from src.executor import AIExecutor


class ThreadsBot(BaseMarketingBot):
    """Threads platform specialist bot.

    Responsibilities:
    - Threads content planning and posting
    - Trend analysis, hashtag strategy
    - Short, impactful text content
    """

    def __init__(
        self,
        own_channel_id: int,
        team_channel_id: int,
        executor: Optional[AIExecutor] = None,
    ):
        super().__init__(
            bot_name="ThreadsBot",
            persona=THREADS_PERSONA,
            own_channel_id=own_channel_id,
            team_channel_id=team_channel_id,
            executor=executor,
        )
