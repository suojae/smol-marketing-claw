"""Smol Claw MCP stdio server — FastMCP entrypoint."""

import builtins
import sys
import os

# === stdout protection ===
# MCP JSON-RPC uses stdout exclusively. Override builtins.print to
# always write to stderr, preventing existing module prints from
# corrupting the protocol. MCP library uses its own transport, not print().
_original_print = builtins.print


def _safe_print(*args, **kwargs):
    kwargs.setdefault("file", sys.stderr)
    _original_print(*args, **kwargs)


builtins.print = _safe_print

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


def main():
    """Run the MCP server via stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
