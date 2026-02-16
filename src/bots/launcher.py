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
    """Create a passthrough executor for all bots.

    Uses McpPassthroughExecutor which generates simple local responses.
    For full LLM responses, connect a real executor (ClaudeExecutor/CodexExecutor).
    """
    try:
        from server.tools._discord_executor import McpPassthroughExecutor
        return McpPassthroughExecutor()
    except ImportError:
        # Fallback: try importing with explicit path setup
        import os, sys
        plugin_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "smol-marketing-claw")
        if plugin_root not in sys.path:
            sys.path.insert(0, plugin_root)
        from server.tools._discord_executor import McpPassthroughExecutor
        return McpPassthroughExecutor()


def _build_bots():
    """Instantiate all 5 bots with their channel configs."""
    team_ch = DISCORD_CHANNELS["team"]
    executor = _create_executor()

    bots = []

    # Team Lead
    token = DISCORD_TOKENS["lead"]
    if token:
        bot = TeamLeadBot(
            own_channel_id=DISCORD_CHANNELS["lead"],
            team_channel_id=team_ch,
            executor=executor,
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
