"""MCP tool for memory search."""

from server.mcp_server import mcp
from server.state import get_state


@mcp.tool()
async def smol_claw_memory_query(query: str, n_results: int = 3) -> dict:
    """Search past decisions from memory.

    Args:
        query: Natural language query to search for similar past decisions.
        n_results: Number of results to return (default: 3, max: 10).
    """
    state = get_state()
    n_results = max(1, min(10, n_results))

    # Recent decisions from JSON memory
    recent_decisions = state.memory.load_decisions()[-n_results:]

    return {
        "recent_decisions": recent_decisions,
    }
