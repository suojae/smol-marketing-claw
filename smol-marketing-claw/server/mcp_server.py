"""Smol Claw MCP HTTP server — FastMCP entrypoint."""

import sys
import os

# Ensure parent directory is on PYTHONPATH so `src.*` imports work
_plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_project_root = os.path.dirname(_plugin_root)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _plugin_root not in sys.path:
    sys.path.insert(0, _plugin_root)

from mcp.server.fastmcp import FastMCP

# Create MCP server instance
mcp = FastMCP(
    "smol-claw",
    instructions="Smol Claw - Autonomous marketing AI with digital hormone system, SNS posting, and Discord integration.",
)

# Import tool modules to register them with mcp
from server.tools import sns_tools  # noqa: F401, E402
from server.tools import hormone_tools  # noqa: F401, E402
from server.tools import think_tool  # noqa: F401, E402
from server.tools import context_tools  # noqa: F401, E402
from server.tools import memory_tools  # noqa: F401, E402
from server.tools import discord_tools  # noqa: F401, E402


HOST = os.getenv("MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("MCP_PORT", "8000"))


def main():
    """Run the MCP server via Streamable HTTP transport."""
    from server.setup import check_and_prompt_env

    check_and_prompt_env(os.path.join(_project_root, ".env"))
    mcp.run(transport="http", host=HOST, port=PORT)


if __name__ == "__main__":
    main()
