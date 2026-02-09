"""Tests for dynamic model switching feature."""

import inspect
from unittest.mock import MagicMock

from src.config import MODEL_ALIASES, DEFAULT_MODEL
from src.executor import ClaudeExecutor
from src.discord_bot import DiscordBot


def test_default_model_is_sonnet():
    assert DEFAULT_MODEL == "sonnet"


def test_model_aliases_has_three_entries():
    assert set(MODEL_ALIASES.keys()) == {"opus", "sonnet", "haiku"}


def test_model_aliases_values_are_valid():
    for alias, model_id in MODEL_ALIASES.items():
        assert model_id.startswith("claude-"), f"{alias} -> {model_id}"


def test_executor_execute_accepts_model_param():
    sig = inspect.signature(ClaudeExecutor.execute)
    assert "model" in sig.parameters
    assert sig.parameters["model"].default is None


def test_discord_bot_initial_model():
    mock_claude = MagicMock(spec=ClaudeExecutor)
    bot = DiscordBot(claude=mock_claude)
    assert bot._current_model == DEFAULT_MODEL
    assert bot._current_model == "sonnet"
