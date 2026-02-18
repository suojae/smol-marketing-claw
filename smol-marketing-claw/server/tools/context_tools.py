"""MCP tool for context collection."""

from server.mcp_server import mcp
from server.state import get_state


@mcp.tool()
async def smol_claw_context() -> dict:
    """Collect current context: git status, TODOs, time, and system info.

    Gathers contextual information useful for autonomous decision making.
    """
    state = get_state()
    context = await state.context_collector.collect()
    return context
