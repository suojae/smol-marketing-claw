"""MCP tools for news search and market research."""

from server.mcp_server import mcp
from server.state import get_state


@mcp.tool()
async def smol_claw_search_news(keyword: str, limit: int = 10) -> dict:
    """Search recent news/tweets for a keyword.

    Uses X Search API to find trending discussions and news.

    Args:
        keyword: Search keyword or query.
        limit: Max results to return (10-100, default: 10).
    """
    state = get_state()

    if state.news_client is None or not state.news_client.is_configured:
        return {
            "success": False,
            "error": "News client not configured. Set NEWS_X_BEARER_TOKEN.",
        }

    result = await state.news_client.search(keyword, limit=limit)

    items = []
    for item in result.items:
        items.append({
            "text": item.text,
            "author": item.author,
            "created_at": item.created_at,
            "url": item.url,
        })

    return {
        "success": result.success,
        "items": items,
        "count": len(items),
        "error": result.error,
    }
