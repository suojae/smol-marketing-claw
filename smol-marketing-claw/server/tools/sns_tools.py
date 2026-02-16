"""MCP tools for SNS posting (X/Twitter, Threads, LinkedIn, Instagram).

Adds manual-approval guardrail: when `CONFIG["require_manual_approval"]`
is true, posts are queued and require explicit approval.
"""

from typing import Callable, Awaitable

from server.mcp_server import mcp
from server.state import get_state
from src.config import CONFIG
from src.approval import enqueue_post


async def _execute_sns_action(
    client,
    action_fn: Callable[[], Awaitable],
    not_configured_msg: str,
) -> dict:
    """Common SNS action executor."""
    if client is None or not client.is_configured:
        return {"success": False, "error": not_configured_msg}

    result = await action_fn()

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
    if CONFIG.get("require_manual_approval", True):
        return await enqueue_post("x", "post", text)
    return await _execute_sns_action(
        client=state.x_client,
        action_fn=lambda: state.x_client.post(text),
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
    if CONFIG.get("require_manual_approval", True):
        return await enqueue_post("x", "reply", text, meta={"tweet_id": tweet_id})
    return await _execute_sns_action(
        client=state.x_client,
        action_fn=lambda: state.x_client.reply(text, tweet_id),
        not_configured_msg="X API not configured.",
    )


@mcp.tool()
async def smol_claw_post_threads(text: str) -> dict:
    """Post to Threads (Meta).

    Args:
        text: The post text (max 500 characters, auto-truncated).
    """
    state = get_state()
    if CONFIG.get("require_manual_approval", True):
        return await enqueue_post("threads", "post", text)
    return await _execute_sns_action(
        client=state.threads_client,
        action_fn=lambda: state.threads_client.post(text),
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
    if CONFIG.get("require_manual_approval", True):
        return await enqueue_post("threads", "reply", text, meta={"post_id": post_id})
    return await _execute_sns_action(
        client=state.threads_client,
        action_fn=lambda: state.threads_client.reply(text, post_id),
        not_configured_msg="Threads API not configured.",
    )


@mcp.tool()
async def smol_claw_post_linkedin(text: str) -> dict:
    """Post to LinkedIn.

    Args:
        text: The post text (max 3000 characters, auto-truncated).
    """
    state = get_state()
    if CONFIG.get("require_manual_approval", True):
        return await enqueue_post("linkedin", "post", text)
    return await _execute_sns_action(
        client=state.linkedin_client,
        action_fn=lambda: state.linkedin_client.post(text),
        not_configured_msg="LinkedIn API not configured. Set LINKEDIN_ACCESS_TOKEN.",
    )


@mcp.tool()
async def smol_claw_post_instagram(text: str, image_url: str) -> dict:
    """Post to Instagram. Requires an image URL.

    Args:
        text: The caption text.
        image_url: Public URL of the image to post.
    """
    state = get_state()
    if CONFIG.get("require_manual_approval", True):
        return await enqueue_post("instagram", "post", text, meta={"image_url": image_url})
    return await _execute_sns_action(
        client=state.instagram_client,
        action_fn=lambda: state.instagram_client.post(text, image_url),
        not_configured_msg="Instagram API not configured. Set INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN.",
    )
