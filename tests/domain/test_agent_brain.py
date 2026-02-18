"""Tests for domain/agent.py — AgentBrain pure logic tests.

No discord import needed — tests use mock ports only.
"""

import asyncio
import tempfile

import pytest

from src.domain.agent import AgentBrain
from src.ports.inbound import IncomingMessage


# --- Mock Ports ---


class MockLLM:
    """Mock LLMPort implementation."""

    def __init__(self, response="mock response"):
        self.response = response
        self.calls = []
        self.usage_tracker = None

    async def execute(self, message, system_prompt=None, session_id=None, model=None):
        self.calls.append({
            "message": message,
            "system_prompt": system_prompt,
            "model": model,
        })
        return self.response


class MockNotification:
    """Mock NotificationPort implementation."""

    def __init__(self):
        self.sent = []
        self.typing_channels = []

    async def send(self, channel_id, text):
        self.sent.append((channel_id, text))

    async def send_typing(self, channel_id):
        self.typing_channels.append(channel_id)


# --- Helpers ---


def _make_brain(
    bot_name="TestBot",
    persona="test persona",
    llm_response="mock response",
    clients=None,
    own_channel_id=100,
    team_channel_ids=None,
):
    tmp = tempfile.mkdtemp()
    llm = MockLLM(response=llm_response)
    notification = MockNotification()
    brain = AgentBrain(
        bot_name=bot_name,
        persona=persona,
        executor=llm,
        clients=clients or {},
        notification=notification,
        own_channel_id=own_channel_id,
        team_channel_ids=team_channel_ids or {200},
        primary_team_channel_id=200,
        storage_dir=tmp,
    )
    return brain, llm, notification


def _make_msg(
    content="hello",
    channel_id=100,
    author_name="user",
    author_id=1,
    is_bot=False,
    is_mention=False,
    is_team_channel=False,
    is_own_channel=True,
):
    return IncomingMessage(
        content=content,
        channel_id=channel_id,
        author_name=author_name,
        author_id=author_id,
        is_bot=is_bot,
        is_mention=is_mention,
        is_team_channel=is_team_channel,
        is_own_channel=is_own_channel,
    )


# --- Tests ---


class TestShouldRespond:
    def test_responds_in_own_channel(self):
        brain, _, _ = _make_brain()
        msg = _make_msg(is_own_channel=True)
        assert brain.should_respond(msg) is True

    def test_responds_when_mentioned_in_team(self):
        brain, _, _ = _make_brain()
        msg = _make_msg(is_own_channel=False, is_team_channel=True, is_mention=True)
        assert brain.should_respond(msg) is True

    def test_ignores_team_without_mention(self):
        brain, _, _ = _make_brain()
        msg = _make_msg(is_own_channel=False, is_team_channel=True, is_mention=False)
        assert brain.should_respond(msg) is False

    def test_ignores_when_inactive(self):
        brain, _, _ = _make_brain()
        brain.active = False
        msg = _make_msg(is_own_channel=True)
        assert brain.should_respond(msg) is False

    def test_bot_responds_when_mentioned_in_team(self):
        brain, _, _ = _make_brain()
        msg = _make_msg(is_bot=True, is_team_channel=True, is_mention=True)
        assert brain.should_respond(msg) is True

    def test_bot_suppressed_after_cancel(self):
        brain, _, _ = _make_brain()
        brain._suppress_bot_replies = True
        msg = _make_msg(is_bot=True, is_team_channel=True, is_mention=True)
        assert brain.should_respond(msg) is False

    def test_bot_in_own_channel_ignored(self):
        brain, _, _ = _make_brain()
        msg = _make_msg(is_bot=True, is_own_channel=True, is_team_channel=False, is_mention=False)
        assert brain.should_respond(msg) is False


class TestChainControl:
    def test_chain_starts_at_zero(self):
        brain, _, _ = _make_brain()
        assert brain.get_chain_count(200) == 0

    def test_increment_chain(self):
        brain, _, _ = _make_brain()
        brain.increment_chain(200)
        assert brain.get_chain_count(200) == 1
        brain.increment_chain(200)
        assert brain.get_chain_count(200) == 2

    def test_reset_chain(self):
        brain, _, _ = _make_brain()
        brain.increment_chain(200)
        brain.increment_chain(200)
        brain.reset_chain(200)
        assert brain.get_chain_count(200) == 0

    def test_reset_clears_suppress(self):
        brain, _, _ = _make_brain()
        brain._suppress_bot_replies = True
        brain.reset_chain(200)
        assert brain._suppress_bot_replies is False


class TestCommands:
    def test_is_command_cancel(self):
        brain, _, _ = _make_brain()
        assert brain.is_command("!cancel") == "!cancel"

    def test_is_command_clear(self):
        brain, _, _ = _make_brain()
        assert brain.is_command("!clear all") == "!clear"

    def test_is_command_alarms(self):
        brain, _, _ = _make_brain()
        assert brain.is_command("!alarms") == "!alarms"

    def test_is_command_help(self):
        brain, _, _ = _make_brain()
        assert brain.is_command("!help") == "!help"

    def test_not_a_command(self):
        brain, _, _ = _make_brain()
        assert brain.is_command("hello world") is None

    def test_empty_string(self):
        brain, _, _ = _make_brain()
        assert brain.is_command("") is None


class TestCancelTasks:
    @pytest.mark.asyncio
    async def test_cancel_own_tasks(self):
        brain, _, _ = _make_brain()

        async def _dummy():
            await asyncio.sleep(9999)

        task = asyncio.create_task(_dummy())
        brain._active_tasks[100] = task
        count = brain.cancel_own_tasks()
        assert count == 1
        await asyncio.sleep(0)  # let cancellation propagate
        assert task.cancelled()

    def test_cancel_no_tasks(self):
        brain, _, _ = _make_brain()
        assert brain.cancel_own_tasks() == 0


class TestHistory:
    def test_build_context_includes_persona(self):
        brain, _, _ = _make_brain(persona="You are a marketing expert.")
        context = brain.build_context(100, "hello")
        assert "You are a marketing expert." in context

    def test_build_context_with_history(self):
        brain, _, _ = _make_brain()
        brain.save_to_history(100, "user msg", "bot reply")
        context = brain.build_context(100, "follow up")
        assert "user: user msg" in context
        assert "assistant: bot reply" in context

    def test_build_context_with_rehire(self):
        brain, _, _ = _make_brain()
        brain._rehired = True
        context = brain.build_context(100, "hello")
        assert "재채용" in context
        assert brain._rehired is False  # cleared after use

    def test_clear_history(self):
        brain, _, _ = _make_brain()
        brain.save_to_history(100, "msg", "reply")
        brain.clear_history()
        assert len(brain._channel_history) == 0

    def test_lru_eviction(self):
        brain, _, _ = _make_brain()
        brain._MAX_CHANNELS = 3
        for i in range(5):
            brain.save_to_history(i, f"msg-{i}", f"reply-{i}")
        # Trigger eviction via build_context for a new channel
        brain.build_context(10, "hello")
        # Should have at most _MAX_CHANNELS
        assert len(brain._channel_history) <= brain._MAX_CHANNELS + 1


class TestActionExecution:
    @pytest.mark.asyncio
    async def test_unknown_action(self):
        brain, _, _ = _make_brain()
        result = await brain.execute_action("UNKNOWN_ACTION", "body")
        assert "알 수 없는 액션" in result

    @pytest.mark.asyncio
    async def test_empty_body_rejected(self):
        brain, _, _ = _make_brain()
        result = await brain.execute_action("POST_X", "")
        assert "비어있음" in result

    @pytest.mark.asyncio
    async def test_no_client_for_platform(self):
        brain, _, _ = _make_brain(clients={})
        result = await brain.execute_action("POST_X", "tweet text")
        assert "연결되지 않았음" in result

    @pytest.mark.asyncio
    async def test_set_alarm_missing_schedule(self):
        brain, _, _ = _make_brain()
        result = await brain.execute_action(
            "SET_ALARM", "prompt: hello", channel_id=100, author="user"
        )
        assert "schedule 필드 누락" in result

    @pytest.mark.asyncio
    async def test_set_alarm_missing_prompt(self):
        brain, _, _ = _make_brain()
        result = await brain.execute_action(
            "SET_ALARM", "schedule: daily 09:00", channel_id=100, author="user"
        )
        assert "prompt 필드 누락" in result

    @pytest.mark.asyncio
    async def test_set_alarm_success(self):
        brain, _, _ = _make_brain()
        result = await brain.execute_action(
            "SET_ALARM",
            "schedule: daily 09:00\nprompt: morning briefing",
            channel_id=100,
            author="user",
        )
        assert "알람 등록 완료" in result
        assert "매일 09:00" in result

    @pytest.mark.asyncio
    async def test_cancel_alarm_not_found(self):
        brain, _, _ = _make_brain()
        result = await brain.execute_action("CANCEL_ALARM", "nonexistent_id")
        assert "찾을 수 없음" in result

    @pytest.mark.asyncio
    async def test_set_alarm_no_context(self):
        brain, _, _ = _make_brain()
        result = await brain.execute_action("SET_ALARM", "schedule: daily 09:00\nprompt: hi")
        assert "메시지 컨텍스트 없음" in result

    @pytest.mark.asyncio
    async def test_search_no_client(self):
        brain, _, _ = _make_brain()
        result = await brain.execute_action("SEARCH_NEWS", "query")
        assert "연결되지 않았음" in result

    @pytest.mark.asyncio
    async def test_instagram_empty_caption(self):
        brain, _, _ = _make_brain(clients={"instagram": object()})
        result = await brain.execute_action("POST_INSTAGRAM", "image_url: https://x.com/img.jpg")
        assert "캡션이 비어있음" in result

    @pytest.mark.asyncio
    async def test_instagram_ssrf_prevention(self):
        brain, _, _ = _make_brain(clients={"instagram": object()})
        result = await brain.execute_action(
            "POST_INSTAGRAM", "caption here\nimage_url: http://evil.com/img.jpg"
        )
        assert "https://" in result


class TestNoDependencyOnDiscord:
    """Verify that domain/agent.py has no discord import."""

    def test_no_discord_import(self):
        import importlib
        import src.domain.agent as mod
        source = importlib.util.find_spec("src.domain.agent").origin
        with open(source) as f:
            code = f.read()
        assert "import discord" not in code
