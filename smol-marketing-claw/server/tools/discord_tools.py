"""MCP tool for Discord bot control."""

import asyncio
import os
import sys

from server.mcp_server import mcp
from server.state import get_state


def _log(msg: str):
    print(msg, file=sys.stderr)


@mcp.tool()
async def smol_claw_discord_control(action: str) -> dict:
    """Control the Discord bot.

    Args:
        action: One of "start", "stop", or "status".
    """
    state = get_state()

    if action == "status":
        if state.discord_bot is None:
            return {"status": "not_initialized", "message": "Discord bot has not been started yet."}
        if state.discord_bot.is_closed():
            return {"status": "stopped", "message": "Discord bot is stopped."}
        return {
            "status": "running",
            "user": str(state.discord_bot.user) if state.discord_bot.user else "connecting...",
        }

    elif action == "start":
        token = os.getenv("DISCORD_BOT_TOKEN", "")
        if not token:
            return {"success": False, "error": "DISCORD_BOT_TOKEN not set."}

        if state.discord_bot is not None and not state.discord_bot.is_closed():
            return {"success": False, "error": "Discord bot is already running."}

        # Import and create bot with MCP passthrough executor
        from src.discord_bot import DiscordBot
        from server.tools._discord_executor import McpPassthroughExecutor

        executor = McpPassthroughExecutor(
            hormones=state.hormones,
            usage_tracker=state.usage_tracker,
        )
        state.discord_bot = DiscordBot(
            executor=executor,
            hormones=state.hormones,
        )

        # Start bot as background task
        async def _run_bot():
            try:
                await state.discord_bot.start(token)
            except Exception as e:
                _log(f"Discord bot error: {e}")

        state._discord_task = asyncio.create_task(_run_bot())
        return {"success": True, "message": "Discord bot starting..."}

    elif action == "stop":
        if state.discord_bot is None or state.discord_bot.is_closed():
            return {"success": False, "error": "Discord bot is not running."}

        await state.discord_bot.close()
        if state._discord_task:
            state._discord_task.cancel()
            state._discord_task = None

        return {"success": True, "message": "Discord bot stopped."}

    else:
        return {"success": False, "error": f"Unknown action: {action}. Use 'start', 'stop', or 'status'."}
