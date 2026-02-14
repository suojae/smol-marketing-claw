"""Tests for dynamic model switching feature."""

import inspect
from unittest.mock import MagicMock

import pytest

from src.config import MODEL_ALIASES, DEFAULT_MODEL, AI_PROVIDER
from src.executor import ClaudeExecutor, CodexExecutor, create_executor
from src.discord_bot import DiscordBot


def test_default_model_is_sonnet():
    assert DEFAULT_MODEL == "sonnet"


def test_model_aliases_has_three_entries():
    assert set(MODEL_ALIASES.keys()) == {"opus", "sonnet", "haiku"}


def test_model_aliases_values_are_valid():
    for alias, model_id in MODEL_ALIASES.items():
        assert isinstance(model_id, str) and model_id.strip(), f"{alias} -> {model_id}"


def test_executor_execute_accepts_model_param():
    sig = inspect.signature(ClaudeExecutor.execute)
    assert "model" in sig.parameters
    assert sig.parameters["model"].default is None


def test_create_executor_uses_current_provider():
    executor = create_executor()
    expected = CodexExecutor if AI_PROVIDER == "codex" else ClaudeExecutor
    assert isinstance(executor, expected)


def test_create_executor_supports_codex():
    assert isinstance(create_executor("codex"), CodexExecutor)


def test_discord_bot_initial_model():
    mock_claude = MagicMock(spec=ClaudeExecutor)
    bot = DiscordBot(executor=mock_claude)
    assert bot._current_model == DEFAULT_MODEL
    assert bot._current_model == "sonnet"


def test_discord_bot_rejects_both_executor_and_claude():
    mock_claude = MagicMock(spec=ClaudeExecutor)
    with pytest.raises(ValueError):
        DiscordBot(executor=mock_claude, claude=mock_claude)
