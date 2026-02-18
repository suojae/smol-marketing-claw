"""Tests for Discord adapter — IncomingMessage conversion."""

import pytest

from src.ports.inbound import IncomingMessage


class TestIncomingMessage:
    def test_creation(self):
        msg = IncomingMessage(
            content="hello",
            channel_id=100,
            author_name="user",
            author_id=1,
            is_bot=False,
            is_mention=True,
            is_team_channel=True,
            is_own_channel=False,
        )
        assert msg.content == "hello"
        assert msg.channel_id == 100
        assert msg.is_mention is True
        assert msg.is_bot is False
        assert msg.is_team_channel is True
        assert msg.is_own_channel is False

    def test_bot_message(self):
        msg = IncomingMessage(
            content="[bot] status update",
            channel_id=200,
            author_name="OtherBot",
            author_id=2,
            is_bot=True,
            is_mention=False,
            is_team_channel=True,
            is_own_channel=False,
        )
        assert msg.is_bot is True
        assert msg.author_name == "OtherBot"

    def test_own_channel(self):
        msg = IncomingMessage(
            content="direct message",
            channel_id=100,
            author_name="user",
            author_id=1,
            is_bot=False,
            is_mention=False,
            is_team_channel=False,
            is_own_channel=True,
        )
        assert msg.is_own_channel is True
        assert msg.is_team_channel is False


class TestNotificationPort:
    def test_discord_notification_adapter_import(self):
        from src.adapters.discord.notification import DiscordNotificationAdapter
        assert DiscordNotificationAdapter is not None

    def test_discord_bot_adapter_import(self):
        from src.adapters.discord.notification import DiscordBotAdapter
        assert DiscordBotAdapter is not None
