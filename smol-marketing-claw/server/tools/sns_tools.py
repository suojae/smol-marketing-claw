"""MCP tools for SNS posting (X/Twitter and Threads)."""

from typing import Callable, Awaitable

from server.mcp_server import mcp
from server.state import get_state


async def _execute_sns_action(
    client,
    action_fn: Callable[[], Awaitable],
    dopamine_reward: float,
    not_configured_msg: str,
) -> dict:
    """Common SNS action executor with hormone feedback."""
    state = get_state()

    if client is None or not client.is_configured:
        return {"success": False, "error": not_configured_msg}

    result = await action_fn()

    if state.hormones:
        if result.success:
            state.hormones.trigger_dopamine(dopamine_reward)
        else:
            state.hormones.trigger_cortisol(0.1)
        state.hormones.save_state()

    return {
        "success": result.success,
        "post_id": result.post_id,
        "text": result.text,
        "error": result.error,
    }


@mcp.tool()
async def smol_claw_post_x(text: str) -> dict:
    """Post a tweet to X (Twitter).

    Args:
        text: The tweet text (max 280 characters, auto-truncated).
    """
    state = get_state()
    return await _execute_sns_action(
        client=state.x_client,
        action_fn=lambda: state.x_client.post(text),
        dopamine_reward=0.1,
        not_configured_msg="X API not configured. Set X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET.",
    )


@mcp.tool()
async def smol_claw_reply_x(text: str, tweet_id: str) -> dict:
    """Reply to a tweet on X (Twitter).

    Args:
        text: The reply text (max 280 characters, auto-truncated).
        tweet_id: The ID of the tweet to reply to.
    """
    state = get_state()
    return await _execute_sns_action(
        client=state.x_client,
        action_fn=lambda: state.x_client.reply(text, tweet_id),
        dopamine_reward=0.05,
        not_configured_msg="X API not configured.",
    )


@mcp.tool()
async def smol_claw_post_threads(text: str) -> dict:
    """Post to Threads (Meta).

    Args:
        text: The post text (max 500 characters, auto-truncated).
    """
    state = get_state()
    return await _execute_sns_action(
        client=state.threads_client,
        action_fn=lambda: state.threads_client.post(text),
        dopamine_reward=0.1,
        not_configured_msg="Threads API not configured. Set THREADS_USER_ID and THREADS_ACCESS_TOKEN.",
    )


@mcp.tool()
async def smol_claw_reply_threads(text: str, post_id: str) -> dict:
    """Reply to a post on Threads (Meta).

    Args:
        text: The reply text (max 500 characters, auto-truncated).
        post_id: The ID of the Threads post to reply to.
    """
    state = get_state()
    return await _execute_sns_action(
        client=state.threads_client,
        action_fn=lambda: state.threads_client.reply(text, post_id),
        dopamine_reward=0.05,
        not_configured_msg="Threads API not configured.",
    )
