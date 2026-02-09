"""Tests for bot persona definition."""

from src.persona import BOT_PERSONA


def test_bot_persona_not_empty():
    assert BOT_PERSONA
    assert len(BOT_PERSONA.strip()) > 0


def test_bot_persona_contains_lean_startup_keywords():
    for keyword in ["Lean Startup", "MVP", "Build-Measure-Learn", "Validated Learning"]:
        assert keyword in BOT_PERSONA, f"Missing keyword: {keyword}"


def test_bot_persona_contains_hooked_keywords():
    for keyword in ["Hook Model", "Trigger", "Variable Reward", "Investment", "Habit Zone"]:
        assert keyword in BOT_PERSONA, f"Missing keyword: {keyword}"


def test_bot_persona_importable_from_package():
    from src import BOT_PERSONA as exported
    assert exported is BOT_PERSONA
