"""Launcher for the 5-bot Discord system."""

import asyncio
import sys

from src.config import DISCORD_CHANNELS, DISCORD_TOKENS
from src.bots.team_lead_bot import TeamLeadBot
from src.bots.threads_bot import ThreadsBot
from src.bots.linkedin_bot import LinkedInBot
from src.bots.instagram_bot import InstagramBot
from src.bots.news_bot import NewsBot


def _log(msg: str):
    print(msg, file=sys.stderr)


def _create_executor():
    """Create an executor for all bots.

    Tries real AI executor first (ClaudeExecutor/CodexExecutor),
    falls back to local passthrough if unavailable.
    """
    try:
        from src.executor import create_executor
        return create_executor()
    except Exception as e:
        _log(f"AI executor unavailable ({e}), using passthrough")

    # Inline minimal passthrough — no sys.path manipulation needed
    from typing import Optional

    class _Passthrough:
        usage_tracker = None

        async def execute(self, message: str, system_prompt: Optional[str] = None,
                          session_id: Optional[str] = None, model: Optional[str] = None) -> str:
            return "메시지 확인했음. (passthrough 모드 — AI executor 미연결)"

    return _Passthrough()


def _create_sns_clients():
    """Create SNS clients with graceful degradation."""
    clients = {}

    try:
        from src.threads_client import ThreadsClient
        c = ThreadsClient()
        if c.is_configured:
            clients["threads"] = c
            _log("ThreadsClient loaded")
        else:
            _log("ThreadsClient not configured — skipping")
    except Exception as e:
        _log(f"ThreadsClient unavailable: {e}")

    try:
        from src.linkedin_client import LinkedInClient
        c = LinkedInClient()
        if c.is_configured:
            clients["linkedin"] = c
            _log("LinkedInClient loaded")
        else:
            _log("LinkedInClient not configured — skipping")
    except Exception as e:
        _log(f"LinkedInClient unavailable: {e}")

    try:
        from src.instagram_client import InstagramClient
        c = InstagramClient()
        if c.is_configured:
            clients["instagram"] = c
            _log("InstagramClient loaded")
        else:
            _log("InstagramClient not configured — skipping")
    except Exception as e:
        _log(f"InstagramClient unavailable: {e}")

    try:
        from src.news_client import NewsClient
        c = NewsClient()
        if c.is_configured:
            clients["news"] = c
            _log("NewsClient loaded")
        else:
            _log("NewsClient not configured — skipping")
    except Exception as e:
        _log(f"NewsClient unavailable: {e}")

    try:
        from src.x_client import XClient
        c = XClient()
        if c.is_configured:
            clients["x"] = c
            _log("XClient loaded")
        else:
            _log("XClient not configured — skipping")
    except Exception as e:
        _log(f"XClient unavailable: {e}")

    return clients


def _build_bots():
    """Instantiate all 5 bots with their channel configs and SNS clients."""
    team_ch = DISCORD_CHANNELS["team"]
    executor = _create_executor()
    sns = _create_sns_clients()

    bots = []

    # Team Lead — X client for POST_X action
    token = DISCORD_TOKENS["lead"]
    if token:
        bot = TeamLeadBot(
            own_channel_id=DISCORD_CHANNELS["lead"],
            team_channel_id=team_ch,
            executor=executor,
            clients={k: v for k, v in sns.items() if k == "x"},
        )
        bots.append((bot, token))
    else:
        _log("Skipping TeamLeadBot — DISCORD_LEAD_TOKEN not set")

    # Threads
    token = DISCORD_TOKENS["threads"]
    if token:
        bot = ThreadsBot(
            own_channel_id=DISCORD_CHANNELS["threads"],
            team_channel_id=team_ch,
            executor=executor,
            clients={k: v for k, v in sns.items() if k == "threads"},
        )
        bots.append((bot, token))
    else:
        _log("Skipping ThreadsBot — DISCORD_THREADS_TOKEN not set")

    # LinkedIn
    token = DISCORD_TOKENS["linkedin"]
    if token:
        bot = LinkedInBot(
            own_channel_id=DISCORD_CHANNELS["linkedin"],
            team_channel_id=team_ch,
            executor=executor,
            clients={k: v for k, v in sns.items() if k == "linkedin"},
        )
        bots.append((bot, token))
    else:
        _log("Skipping LinkedInBot — DISCORD_LINKEDIN_TOKEN not set")

    # Instagram
    token = DISCORD_TOKENS["instagram"]
    if token:
        bot = InstagramBot(
            own_channel_id=DISCORD_CHANNELS["instagram"],
            team_channel_id=team_ch,
            executor=executor,
            clients={k: v for k, v in sns.items() if k == "instagram"},
        )
        bots.append((bot, token))
    else:
        _log("Skipping InstagramBot — DISCORD_INSTAGRAM_TOKEN not set")

    # News
    token = DISCORD_TOKENS["news"]
    if token:
        bot = NewsBot(
            own_channel_id=DISCORD_CHANNELS["news"],
            team_channel_id=team_ch,
            executor=executor,
            clients={k: v for k, v in sns.items() if k == "news"},
        )
        bots.append((bot, token))
    else:
        _log("Skipping NewsBot — DISCORD_NEWS_TOKEN not set")

    return bots


async def launch_all_bots():
    """Launch all configured bots concurrently."""
    bots = _build_bots()

    if not bots:
        _log("No bots configured. Set DISCORD_*_TOKEN environment variables.")
        return

    _log(f"Launching {len(bots)} bot(s)...")

    async def _run(bot, token):
        try:
            await bot.start(token)
        except Exception as e:
            _log(f"[{bot.bot_name}] crashed: {e}")

    await asyncio.gather(*[_run(bot, token) for bot, token in bots])


if __name__ == "__main__":
    asyncio.run(launch_all_bots())
