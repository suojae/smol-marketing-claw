"""Tests for the new typed AppConfig dataclass."""

import pytest

from src.config import AppConfig, DiscordConfig, SNSConfig, UsageLimitsConfig


class TestUsageLimitsConfig:
    def test_defaults(self):
        c = UsageLimitsConfig()
        assert c.max_calls_per_minute == 60
        assert c.max_calls_per_hour == 500
        assert c.max_calls_per_day == 10000
        assert c.paused is False

    def test_custom(self):
        c = UsageLimitsConfig(max_calls_per_day=100, paused=True)
        assert c.max_calls_per_day == 100
        assert c.paused is True


class TestSNSConfig:
    def test_defaults_empty(self):
        c = SNSConfig()
        assert c.x_consumer_key == ""
        assert c.threads_user_id == ""

    def test_custom(self):
        c = SNSConfig(x_consumer_key="key123")
        assert c.x_consumer_key == "key123"


class TestDiscordConfig:
    def test_defaults_empty(self):
        c = DiscordConfig()
        assert c.channels == {}
        assert c.tokens == {}


class TestAppConfig:
    def test_defaults(self):
        c = AppConfig()
        assert c.port == 3000
        assert c.ai_provider == "claude"
        assert c.require_manual_approval is True
        assert isinstance(c.sns, SNSConfig)
        assert isinstance(c.discord, DiscordConfig)
        assert isinstance(c.usage_limits, UsageLimitsConfig)

    def test_from_env(self):
        c = AppConfig.from_env()
        assert c.session_id  # should have a UUID
        assert c.ai_provider in ("claude", "codex")

    def test_from_env_idempotent_session_id(self):
        """from_env() should reuse CONFIG's session_id, not generate a new one."""
        c1 = AppConfig.from_env()
        c2 = AppConfig.from_env()
        assert c1.session_id == c2.session_id

    def test_custom(self):
        c = AppConfig(
            port=8080,
            require_manual_approval=False,
            sns=SNSConfig(x_consumer_key="mykey"),
        )
        assert c.port == 8080
        assert c.require_manual_approval is False
        assert c.sns.x_consumer_key == "mykey"
