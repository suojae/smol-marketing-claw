"""Unit tests for ThreadsClient."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from aiohttp import ClientSession

from src.threads_client import ThreadsClient, ThreadsPostResult, THREADS_API_BASE


@pytest.fixture
def threads_configured(monkeypatch):
    monkeypatch.setattr("src.threads_client.CONFIG", {
        "threads_user_id": "user123",
        "threads_access_token": "tok456",
    })


@pytest.fixture
def threads_unconfigured(monkeypatch):
    monkeypatch.setattr("src.threads_client.CONFIG", {
        "threads_user_id": "",
        "threads_access_token": "",
    })


class TestIsConfigured:
    def test_configured(self, threads_configured):
        client = ThreadsClient()
        assert client.is_configured is True

    def test_unconfigured(self, threads_unconfigured):
        client = ThreadsClient()
        assert client.is_configured is False

    def test_partial(self, monkeypatch):
        monkeypatch.setattr("src.threads_client.CONFIG", {
            "threads_user_id": "user123",
            "threads_access_token": "",
        })
        client = ThreadsClient()
        assert client.is_configured is False


class TestTruncateText:
    def test_short_text(self):
        assert ThreadsClient.truncate_text("hello") == "hello"

    def test_exact_limit(self):
        text = "a" * 500
        assert ThreadsClient.truncate_text(text) == text

    def test_over_limit(self):
        text = "a" * 600
        result = ThreadsClient.truncate_text(text)
        assert len(result) == 500
        assert result.endswith("...")

    def test_custom_limit(self):
        text = "a" * 50
        result = ThreadsClient.truncate_text(text, limit=20)
        assert len(result) == 20
        assert result.endswith("...")


def _mock_aiohttp_session(responses):
    """Return a mock that replaces aiohttp.ClientSession context manager.
    responses: list of dicts, each consumed in order by successive post() calls.
    """
    call_idx = 0

    class FakeResponse:
        def __init__(self, data):
            self._data = data

        async def json(self):
            return self._data

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class FakeSession:
        def post(self, url, **kwargs):
            nonlocal call_idx
            resp = FakeResponse(responses[call_idx])
            call_idx += 1
            return resp

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    return FakeSession


class TestPost:
    @pytest.mark.asyncio
    async def test_post_success(self, threads_configured):
        mock_session = _mock_aiohttp_session([
            {"id": "container_1"},  # create container
            {"id": "post_1"},       # publish
        ])
        client = ThreadsClient()
        with patch("src.threads_client.aiohttp.ClientSession", mock_session):
            result = await client.post("Hello Threads")
        assert result.success is True
        assert result.post_id == "post_1"
        assert result.text == "Hello Threads"

    @pytest.mark.asyncio
    async def test_post_container_error(self, threads_configured):
        mock_session = _mock_aiohttp_session([
            {"error": {"message": "Invalid token"}},
        ])
        client = ThreadsClient()
        with patch("src.threads_client.aiohttp.ClientSession", mock_session):
            result = await client.post("Hello")
        assert result.success is False
        assert "Invalid token" in result.error

    @pytest.mark.asyncio
    async def test_post_publish_error(self, threads_configured):
        mock_session = _mock_aiohttp_session([
            {"id": "container_1"},
            {"error": {"message": "Publish failed"}},
        ])
        client = ThreadsClient()
        with patch("src.threads_client.aiohttp.ClientSession", mock_session):
            result = await client.post("Hello")
        assert result.success is False
        assert "Publish failed" in result.error

    @pytest.mark.asyncio
    async def test_post_truncates(self, threads_configured):
        mock_session = _mock_aiohttp_session([
            {"id": "c1"},
            {"id": "p1"},
        ])
        client = ThreadsClient()
        with patch("src.threads_client.aiohttp.ClientSession", mock_session):
            result = await client.post("x" * 600)
        assert result.success is True
        assert len(result.text) == 500


class TestReply:
    @pytest.mark.asyncio
    async def test_reply_success(self, threads_configured):
        mock_session = _mock_aiohttp_session([
            {"id": "container_r"},
            {"id": "reply_1"},
        ])
        client = ThreadsClient()
        with patch("src.threads_client.aiohttp.ClientSession", mock_session):
            result = await client.reply("Reply text", "post_1")
        assert result.success is True
        assert result.post_id == "reply_1"

    @pytest.mark.asyncio
    async def test_reply_failure(self, threads_configured):
        mock_session = _mock_aiohttp_session([
            {"error": {"message": "Not found"}},
        ])
        client = ThreadsClient()
        with patch("src.threads_client.aiohttp.ClientSession", mock_session):
            result = await client.reply("Reply", "bad_id")
        assert result.success is False
        assert "Not found" in result.error


class TestThreadsPostResult:
    def test_defaults(self):
        r = ThreadsPostResult(success=True)
        assert r.post_id is None
        assert r.text is None
        assert r.error is None

    def test_full(self):
        r = ThreadsPostResult(success=False, error="oops")
        assert r.error == "oops"
