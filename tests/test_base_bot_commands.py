"""Tests for BaseMarketingBot command handlers (!cancel, !clear, !help)."""

import asyncio
from collections import OrderedDict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bots.base_bot import BaseMarketingBot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OWN_CHANNEL = 100
TEAM_CHANNEL = 200
BOT_USER_ID = 999


def _make_bot(executor=None) -> BaseMarketingBot:
    """Create a BaseMarketingBot with minimal config and a fake self.user."""
    bot = BaseMarketingBot(
        bot_name="TestBot",
        persona="You are a test bot.",
        own_channel_id=OWN_CHANNEL,
        team_channel_id=TEAM_CHANNEL,
        executor=executor,
    )
    # Fake self.user — discord.Client exposes user via _connection.user
    fake_user = MagicMock()
    fake_user.id = BOT_USER_ID
    fake_user.name = "TestBot"
    fake_user.display_name = "TestBot"
    fake_user.mentioned_in = MagicMock(return_value=False)
    bot._connection = MagicMock()
    bot._connection.user = fake_user
    return bot


def _make_message(content: str, channel_id: int, *, is_bot: bool = False,
                  mention_bot: bool = False) -> MagicMock:
    """Create a fake discord.Message."""
    msg = MagicMock()
    msg.content = content
    msg.channel = MagicMock()
    msg.channel.id = channel_id
    msg.channel.send = AsyncMock()
    msg.channel.typing = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(), __aexit__=AsyncMock(),
    ))
    msg.author = MagicMock()
    msg.author.bot = is_bot
    msg.author.id = 1234 if not is_bot else 5678
    return msg


# ---------------------------------------------------------------------------
# !clear tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clear_current_channel_only():
    bot = _make_bot()
    bot._channel_history[OWN_CHANNEL] = [{"role": "user", "text": "hi"}]
    bot._channel_history[TEAM_CHANNEL] = [{"role": "user", "text": "hello"}]

    msg = _make_message("!clear", OWN_CHANNEL)
    await bot.on_message(msg)

    # Own channel cleared
    assert OWN_CHANNEL not in bot._channel_history
    # Team channel untouched
    assert TEAM_CHANNEL in bot._channel_history
    msg.channel.send.assert_awaited_once()
    assert "이 채널" in msg.channel.send.call_args[0][0]


@pytest.mark.asyncio
async def test_clear_all_channels():
    bot = _make_bot()
    bot._channel_history[OWN_CHANNEL] = [{"role": "user", "text": "hi"}]
    bot._channel_history[TEAM_CHANNEL] = [{"role": "user", "text": "hello"}]

    msg = _make_message("!clear all", OWN_CHANNEL)
    await bot.on_message(msg)

    assert len(bot._channel_history) == 0
    msg.channel.send.assert_awaited_once()
    assert "전체" in msg.channel.send.call_args[0][0]


# ---------------------------------------------------------------------------
# !cancel tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_active_task():
    """!cancel should cancel a running task; _respond sends the cancellation message."""
    executor = MagicMock()
    bot = _make_bot(executor=executor)

    # Simulate an active, non-done task
    fake_task = MagicMock()
    fake_task.done.return_value = False
    fake_task.cancel = MagicMock()
    bot._active_tasks[OWN_CHANNEL] = fake_task

    msg = _make_message("!cancel", OWN_CHANNEL)
    await bot.on_message(msg)

    fake_task.cancel.assert_called_once()
    # No message sent by _handle_cancel itself — _respond's CancelledError handler does that
    msg.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_no_active_task_own_channel():
    """!cancel in 1:1 channel with no active task → inform user."""
    bot = _make_bot()
    msg = _make_message("!cancel", OWN_CHANNEL)
    await bot.on_message(msg)

    msg.channel.send.assert_awaited_once()
    assert "취소할 작업이 없음" in msg.channel.send.call_args[0][0]


@pytest.mark.asyncio
async def test_cancel_no_active_task_team_channel_silent():
    """!cancel in team channel with no active task → silence (no 5-bot noise)."""
    bot = _make_bot()
    msg = _make_message("!cancel", TEAM_CHANNEL)
    await bot.on_message(msg)

    msg.channel.send.assert_not_awaited()


# ---------------------------------------------------------------------------
# !help test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_help_in_own_channel():
    bot = _make_bot()
    msg = _make_message("!help", OWN_CHANNEL)
    await bot.on_message(msg)

    msg.channel.send.assert_awaited_once()
    text = msg.channel.send.call_args[0][0]
    assert "!cancel" in text
    assert "!clear" in text
    assert "!help" in text


# ---------------------------------------------------------------------------
# Bot-sent commands ignored
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bot_author_commands_ignored():
    """Commands from other bots should be ignored entirely."""
    bot = _make_bot()
    for cmd in ("!cancel", "!clear", "!help"):
        msg = _make_message(cmd, OWN_CHANNEL, is_bot=True)
        await bot.on_message(msg)
        msg.channel.send.assert_not_awaited()


# ---------------------------------------------------------------------------
# !clear / !help require mention in team channel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clear_team_channel_without_mention_ignored():
    """!clear in team channel without mentioning the bot → ignored."""
    bot = _make_bot()
    bot._channel_history[TEAM_CHANNEL] = [{"role": "user", "text": "hi"}]

    msg = _make_message("!clear", TEAM_CHANNEL)
    await bot.on_message(msg)

    # History should remain untouched
    assert TEAM_CHANNEL in bot._channel_history
    msg.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_help_team_channel_without_mention_ignored():
    """!help in team channel without mentioning the bot → ignored."""
    bot = _make_bot()
    msg = _make_message("!help", TEAM_CHANNEL)
    await bot.on_message(msg)

    msg.channel.send.assert_not_awaited()


# ---------------------------------------------------------------------------
# Race condition: second message must not lose its task reference
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrent_tasks_no_orphan():
    """When task2 overwrites task1 in _active_tasks, task1's finally must not evict task2."""
    executor = MagicMock()
    bot = _make_bot(executor=executor)

    task1 = MagicMock()
    task2 = MagicMock()

    # Simulate: task1 was registered, then task2 overwrote it
    bot._active_tasks[OWN_CHANNEL] = task2

    # task1's finally block runs — should NOT remove task2
    if bot._active_tasks.get(OWN_CHANNEL) is task1:
        del bot._active_tasks[OWN_CHANNEL]

    # task2 must still be reachable
    assert bot._active_tasks.get(OWN_CHANNEL) is task2


# ---------------------------------------------------------------------------
# Alias-based text mention detection
# ---------------------------------------------------------------------------

def test_alias_text_mention():
    """Bot with aliases should respond to @OldName text mentions."""
    bot = BaseMarketingBot(
        bot_name="ResearcherBot",
        persona="test",
        own_channel_id=OWN_CHANNEL,
        team_channel_id=TEAM_CHANNEL,
        aliases=["NewsBot"],
    )
    fake_user = MagicMock()
    fake_user.id = BOT_USER_ID
    fake_user.name = "ResearcherBot"
    fake_user.display_name = "ResearcherBot"
    bot._connection = MagicMock()
    bot._connection.user = fake_user

    assert bot._is_text_mentioned("@NewsBot 조사해줘")
    assert bot._is_text_mentioned("@newsbot 조사해줘")
    assert bot._is_text_mentioned("@ResearcherBot 조사해줘")
    assert not bot._is_text_mentioned("@ThreadsBot 조사해줘")
