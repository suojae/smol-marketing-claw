"""Unit tests for XClient."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from types import SimpleNamespace

from src.x_client import XClient, XPostResult


@pytest.fixture(autouse=True)
def _clear_client():
    """Reset module-level state between tests."""
    yield


@pytest.fixture
def x_configured(monkeypatch):
    """Patch CONFIG so X keys are present."""
    fake = {
        "x_consumer_key": "ck",
        "x_consumer_secret": "cs",
        "x_access_token": "at",
        "x_access_token_secret": "ats",
    }
    monkeypatch.setattr("src.x_client.CONFIG", {**fake})
    return fake


@pytest.fixture
def x_unconfigured(monkeypatch):
    monkeypatch.setattr("src.x_client.CONFIG", {
        "x_consumer_key": "",
        "x_consumer_secret": "",
        "x_access_token": "",
        "x_access_token_secret": "",
    })


class TestIsConfigured:
    def test_configured(self, x_configured):
        client = XClient()
        assert client.is_configured is True

    def test_unconfigured(self, x_unconfigured):
        client = XClient()
        assert client.is_configured is False

    def test_partial(self, monkeypatch):
        monkeypatch.setattr("src.x_client.CONFIG", {
            "x_consumer_key": "ck",
            "x_consumer_secret": "",
            "x_access_token": "at",
            "x_access_token_secret": "ats",
        })
        client = XClient()
        assert client.is_configured is False


class TestTruncateText:
    def test_short_text(self):
        assert XClient.truncate_text("hello") == "hello"

    def test_exact_limit(self):
        text = "a" * 280
        assert XClient.truncate_text(text) == text

    def test_over_limit(self):
        text = "a" * 300
        result = XClient.truncate_text(text)
        assert len(result) == 280
        assert result.endswith("...")

    def test_custom_limit(self):
        text = "a" * 50
        result = XClient.truncate_text(text, limit=20)
        assert len(result) == 20
        assert result.endswith("...")


class TestPost:
    @pytest.mark.asyncio
    async def test_post_success(self, x_configured):
        client = XClient()
        mock_tweepy = MagicMock()
        mock_tweepy.create_tweet.return_value = SimpleNamespace(
            data={"id": "12345"}
        )
        client._client = mock_tweepy

        result = await client.post("Hello world")
        assert result.success is True
        assert result.post_id == "12345"
        assert result.text == "Hello world"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_post_failure(self, x_configured):
        client = XClient()
        mock_tweepy = MagicMock()
        mock_tweepy.create_tweet.side_effect = Exception("API error")
        client._client = mock_tweepy

        result = await client.post("Hello world")
        assert result.success is False
        assert result.post_id is None
        assert result.error == "API error"

    @pytest.mark.asyncio
    async def test_post_truncates(self, x_configured):
        client = XClient()
        mock_tweepy = MagicMock()
        mock_tweepy.create_tweet.return_value = SimpleNamespace(
            data={"id": "99"}
        )
        client._client = mock_tweepy

        long = "x" * 300
        result = await client.post(long)
        assert result.success is True
        assert len(result.text) == 280


class TestReply:
    @pytest.mark.asyncio
    async def test_reply_success(self, x_configured):
        client = XClient()
        mock_tweepy = MagicMock()
        mock_tweepy.create_tweet.return_value = SimpleNamespace(
            data={"id": "67890"}
        )
        client._client = mock_tweepy

        result = await client.reply("Reply text", "12345")
        assert result.success is True
        assert result.post_id == "67890"
        mock_tweepy.create_tweet.assert_called_once_with(
            text="Reply text", in_reply_to_tweet_id="12345"
        )

    @pytest.mark.asyncio
    async def test_reply_failure(self, x_configured):
        client = XClient()
        mock_tweepy = MagicMock()
        mock_tweepy.create_tweet.side_effect = Exception("Not found")
        client._client = mock_tweepy

        result = await client.reply("Reply text", "12345")
        assert result.success is False
        assert result.error == "Not found"


class TestXPostResult:
    def test_defaults(self):
        r = XPostResult(success=True)
        assert r.post_id is None
        assert r.text is None
        assert r.error is None

    def test_full(self):
        r = XPostResult(success=True, post_id="1", text="hi", error=None)
        assert r.post_id == "1"
