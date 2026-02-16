"""MCP tool for system status."""

from server.mcp_server import mcp
from server.state import get_state


@mcp.tool()
async def smol_claw_status() -> dict:
    """Return system status: usage stats and SNS configuration.

    Use this to check API usage and which SNS platforms are configured.
    """
    state = get_state()
    usage_status = state.usage_tracker.get_status()

    sns_config = {
        "x_configured": state.x_client is not None and state.x_client.is_configured,
        "threads_configured": state.threads_client is not None and state.threads_client.is_configured,
        "linkedin_configured": state.linkedin_client is not None and state.linkedin_client.is_configured,
        "instagram_configured": state.instagram_client is not None and state.instagram_client.is_configured,
        "news_configured": state.news_client is not None and state.news_client.is_configured,
    }

    return {
        "usage": usage_status,
        "sns": sns_config,
    }
