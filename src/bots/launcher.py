"""Launcher for the 5-bot Discord system."""

import asyncio
import sys

from src.config import DISCORD_CHANNELS, DISCORD_TOKENS
from src.bots.team_lead_bot import TeamLeadBot
from src.bots.threads_bot import ThreadsBot
from src.bots.linkedin_bot import LinkedInBot
from src.bots.instagram_bot import InstagramBot
from src.bots.news_bot import ResearcherBot


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
    test_ch = DISCORD_CHANNELS.get("test", 0)
    extra = [test_ch] if test_ch else []
    sns = _create_sns_clients()

    # Bot definitions: (Class, token_key, sns_filter)
    _BOT_DEFS = [
        (TeamLeadBot, "lead", {"x"}),
        (ThreadsBot, "threads", {"threads"}),
        (LinkedInBot, "linkedin", {"linkedin"}),
        (InstagramBot, "instagram", {"instagram"}),
        (ResearcherBot, "news", {"news"}),
    ]

    bots = []
    for BotClass, key, allowed_sns in _BOT_DEFS:
        token = DISCORD_TOKENS[key]
        if not token:
            _log(f"Skipping {BotClass.__name__} — DISCORD_{key.upper()}_TOKEN not set")
            continue
        bot = BotClass(
            own_channel_id=DISCORD_CHANNELS[key],
            team_channel_id=team_ch,
            extra_team_channels=extra,
            executor=_create_executor(),  # independent executor per bot
            clients={k: v for k, v in sns.items() if k in allowed_sns},
        )
        bots.append((bot, token))

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
