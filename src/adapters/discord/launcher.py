"""Launcher for the multi-bot Discord system."""

import asyncio
import sys
from typing import Dict

from src.config import DISCORD_CHANNELS, DISCORD_TOKENS
from src.adapters.discord.base_bot import BaseMarketingBot
from src.adapters.storage.persona_store import PersonaStore


def _log(msg: str):
    print(msg, file=sys.stderr)


def _create_executor():
    """Create an executor for all bots.

    Tries real AI executor first (ClaudeExecutor/CodexExecutor),
    falls back to local passthrough if unavailable.
    """
    try:
        from src.adapters.llm.executor import create_executor
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
        from src.adapters.sns.threads import ThreadsClient
        c = ThreadsClient()
        if c.is_configured:
            clients["threads"] = c
            _log("ThreadsClient loaded")
        else:
            _log("ThreadsClient not configured — skipping")
    except Exception as e:
        _log(f"ThreadsClient unavailable: {e}")

    try:
        from src.adapters.sns.instagram import InstagramClient
        c = InstagramClient()
        if c.is_configured:
            clients["instagram"] = c
            _log("InstagramClient loaded")
        else:
            _log("InstagramClient not configured — skipping")
    except Exception as e:
        _log(f"InstagramClient unavailable: {e}")

    try:
        from src.adapters.sns.x import XClient
        c = XClient()
        if c.is_configured:
            clients["x"] = c
            _log("XClient loaded")
        else:
            _log("XClient not configured — skipping")
    except Exception as e:
        _log(f"XClient unavailable: {e}")

    return clients


_BOT_REGISTRY: Dict[str, BaseMarketingBot] = {}


def _build_bots():
    """Instantiate all bots with their channel configs and SNS clients."""
    _BOT_REGISTRY.clear()

    team_ch = DISCORD_CHANNELS["team"]
    test_ch = DISCORD_CHANNELS.get("test", 0)
    extra = [test_ch] if test_ch else []
    sns = _create_sns_clients()
    persona_store = PersonaStore()

    # Bot definitions: (token_key, bot_name, sns_filter, aliases)
    _BOT_DEFS = [
        ("threads", "ThreadsBot", {"threads"}, []),
        ("instagram", "InstagramBot", {"instagram"}, []),
        ("hr", "HRBot", set(), ["HR"]),
    ]

    bots = []
    for key, bot_name, allowed_sns, aliases in _BOT_DEFS:
        token = DISCORD_TOKENS[key]
        if not token:
            _log(f"Skipping {bot_name} — DISCORD_{key.upper()}_TOKEN not set")
            continue
        bot = BaseMarketingBot(
            bot_name=bot_name,
            own_channel_id=DISCORD_CHANNELS[key],
            team_channel_id=team_ch,
            extra_team_channels=extra,
            persona_store=persona_store,
            executor=_create_executor(),
            clients={k: v for k, v in sns.items() if k in allowed_sns},
            aliases=aliases,
        )
        _BOT_REGISTRY[key] = bot
        bots.append((bot, token))

    # Inject bot_registry into all bots (HR authority + !cancel all cross-bot)
    for bot_instance, _ in bots:
        bot_instance.bot_registry = _BOT_REGISTRY

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
