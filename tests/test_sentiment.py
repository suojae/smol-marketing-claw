"""Tests for sentiment-based hormone triggers in DiscordBot."""

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

from src.discord_bot import DiscordBot
from src.config import MODEL_ALIASES


def run(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.run(coro)


def _make_bot(mock_claude, hormones):
    with patch.dict("os.environ", {"DISCORD_CHANNEL_ID": "0"}):
        return DiscordBot(executor=mock_claude, hormones=hormones)


class TestPraiseMessage:
    def test_praise_triggers_dopamine(self):
        """Praise should trigger positive dopamine delta."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = json.dumps(
            {"dopamine_delta": 0.15, "cortisol_delta": -0.05}
        )
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("잘했어! 정말 대단해!"))

        mock_hormones.trigger_dopamine.assert_called_once_with(0.15)
        mock_hormones.trigger_cortisol.assert_called_once_with(-0.05)


class TestCriticismMessage:
    def test_criticism_triggers_cortisol(self):
        """Criticism should trigger positive cortisol delta."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = json.dumps(
            {"dopamine_delta": -0.1, "cortisol_delta": 0.18}
        )
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("왜 이렇게 못하냐? 빨리 제대로 해!"))

        mock_hormones.trigger_dopamine.assert_called_once_with(-0.1)
        mock_hormones.trigger_cortisol.assert_called_once_with(0.18)


class TestNeutralMessage:
    def test_neutral_no_trigger(self):
        """Neutral message should not trigger any hormone change."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = json.dumps(
            {"dopamine_delta": 0.0, "cortisol_delta": 0.0}
        )
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("오늘 날씨 어때?"))

        mock_hormones.trigger_dopamine.assert_not_called()
        mock_hormones.trigger_cortisol.assert_not_called()


class TestParseFailure:
    def test_invalid_json_no_crash(self):
        """Invalid JSON should be silently ignored."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = "this is not json"
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("아무 메시지"))

        mock_hormones.trigger_dopamine.assert_not_called()
        mock_hormones.trigger_cortisol.assert_not_called()

    def test_executor_exception_no_crash(self):
        """Executor failure should be silently ignored."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.side_effect = Exception("API error")
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("아무 메시지"))

        mock_hormones.trigger_dopamine.assert_not_called()
        mock_hormones.trigger_cortisol.assert_not_called()


class TestHormonesDisabled:
    def test_skip_when_no_hormones(self):
        """Should skip analysis entirely when hormones is None."""
        mock_claude = AsyncMock()
        bot = _make_bot(mock_claude, hormones=None)

        run(bot._analyze_sentiment("칭찬해줄게!"))

        mock_claude.execute.assert_not_called()


class TestDeltaClamping:
    def test_clamps_to_max(self):
        """Deltas exceeding 0.2 should be clamped."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = json.dumps(
            {"dopamine_delta": 0.5, "cortisol_delta": -0.5}
        )
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("극단적 메시지"))

        mock_hormones.trigger_dopamine.assert_called_once_with(0.2)
        mock_hormones.trigger_cortisol.assert_called_once_with(-0.2)


class TestCodeFenceStripping:
    def test_strips_markdown_fences(self):
        """Should handle haiku responses wrapped in markdown code fences."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = (
            '```json\n{"dopamine_delta": 0.1, "cortisol_delta": 0.0}\n```'
        )
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("고마워!"))

        mock_hormones.trigger_dopamine.assert_called_once_with(0.1)
        mock_hormones.trigger_cortisol.assert_not_called()


# --- Helper to build a fake Discord message for on_message tests ---

def _make_discord_message(bot, text="Hello"):
    """Create a minimal mock Discord message for on_message tests."""
    msg = MagicMock()
    msg.content = text
    msg.author = MagicMock()
    msg.author.__eq__ = lambda self, other: False  # not the bot itself
    msg.channel = MagicMock()
    msg.channel.id = bot.channel_id or 123
    msg.channel.send = AsyncMock()

    @asynccontextmanager
    async def fake_typing():
        yield

    msg.channel.typing = fake_typing
    return msg


@dataclass
class _FakeParams:
    model: str = "sonnet"
    persona_modifier: str = ""


# --- New tests: hormone → response context injection ---

class TestHormoneContextInjection:
    """Verify that hormone persona_modifier is injected into the system prompt."""

    def test_persona_modifier_in_context(self):
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()

        fake_params = _FakeParams(
            model="sonnet",
            persona_modifier="[Emotional state: calm and focused]",
        )
        mock_hormones.get_control_params.return_value = fake_params

        # Sentiment returns neutral
        mock_claude.execute.side_effect = [
            json.dumps({"dopamine_delta": 0.0, "cortisol_delta": 0.0}),
            "Bot response",
        ]

        bot = _make_bot(mock_claude, mock_hormones)
        bot.channel_id = 123
        msg = _make_discord_message(bot, "안녕하세요")

        run(bot.on_message(msg))

        # The main execute call (second call) should include persona_modifier
        main_call = mock_claude.execute.call_args_list[1]
        system_prompt = main_call.kwargs.get("system_prompt", main_call.args[1] if len(main_call.args) > 1 else "")
        assert "[Emotional state: calm and focused]" in system_prompt

    def test_empty_persona_modifier_not_injected(self):
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()

        fake_params = _FakeParams(model="sonnet", persona_modifier="")
        mock_hormones.get_control_params.return_value = fake_params

        mock_claude.execute.side_effect = [
            json.dumps({"dopamine_delta": 0.0, "cortisol_delta": 0.0}),
            "Bot response",
        ]

        bot = _make_bot(mock_claude, mock_hormones)
        bot.channel_id = 123
        msg = _make_discord_message(bot, "test")

        run(bot.on_message(msg))

        # system_prompt should NOT contain double newlines from empty modifier
        main_call = mock_claude.execute.call_args_list[1]
        system_prompt = main_call.kwargs.get("system_prompt", main_call.args[1] if len(main_call.args) > 1 else "")
        # Should go straight from BOT_PERSONA to "Continue naturally."
        assert "\n\n\n\n" not in system_prompt


class TestHormoneModelSelection:
    """Verify that hormone-based model overrides the manual selection."""

    def test_hormone_model_used(self):
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()

        fake_params = _FakeParams(model="haiku", persona_modifier="stressed")
        mock_hormones.get_control_params.return_value = fake_params

        mock_claude.execute.side_effect = [
            json.dumps({"dopamine_delta": 0.0, "cortisol_delta": 0.0}),
            "Bot response",
        ]

        bot = _make_bot(mock_claude, mock_hormones)
        bot.channel_id = 123
        bot._current_model = "sonnet"  # manual selection = sonnet
        msg = _make_discord_message(bot, "test")

        run(bot.on_message(msg))

        main_call = mock_claude.execute.call_args_list[1]
        used_model = main_call.kwargs.get("model", "")
        assert used_model == MODEL_ALIASES["haiku"]

    def test_manual_model_when_no_hormones(self):
        mock_claude = AsyncMock()

        mock_claude.execute.return_value = "Bot response"

        bot = _make_bot(mock_claude, hormones=None)
        bot.channel_id = 123
        bot._current_model = "opus"
        msg = _make_discord_message(bot, "test")

        run(bot.on_message(msg))

        main_call = mock_claude.execute.call_args_list[0]
        used_model = main_call.kwargs.get("model", "")
        assert used_model == MODEL_ALIASES["opus"]


class TestHormoneDecay:
    """Verify that decay() is called once per message."""

    def test_decay_called_per_message(self):
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()

        fake_params = _FakeParams(model="sonnet", persona_modifier="")
        mock_hormones.get_control_params.return_value = fake_params

        mock_claude.execute.side_effect = [
            json.dumps({"dopamine_delta": 0.0, "cortisol_delta": 0.0}),
            "Bot response",
        ]

        bot = _make_bot(mock_claude, mock_hormones)
        bot.channel_id = 123
        msg = _make_discord_message(bot, "test")

        run(bot.on_message(msg))

        mock_hormones.decay.assert_called_once()

    def test_no_decay_without_hormones(self):
        mock_claude = AsyncMock()
        mock_claude.execute.return_value = "Bot response"

        bot = _make_bot(mock_claude, hormones=None)
        bot.channel_id = 123
        msg = _make_discord_message(bot, "test")

        run(bot.on_message(msg))
        # No crash — just verify it ran without error
