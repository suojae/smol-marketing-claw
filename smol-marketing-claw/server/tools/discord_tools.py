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
    """Control the multi-bot Discord system.

    Args:
        action: One of "start", "stop", or "status".
    """
    state = get_state()

    if action == "status":
        return {"status": "Use src/adapters/discord/launcher.py to manage Discord bots independently."}

    elif action == "start":
        return {
            "success": False,
            "message": "Discord bots are now managed via src/adapters/discord/launcher.py. "
                       "Run: python -c \"import asyncio; from src.adapters.discord.launcher import launch_all_bots; asyncio.run(launch_all_bots())\"",
        }

    elif action == "stop":
        return {
            "success": False,
            "message": "Discord bots are managed independently. Stop the launcher process to shut down all bots.",
        }

    else:
        return {"success": False, "error": f"Unknown action: {action}. Use 'start', 'stop', or 'status'."}
