"""Unit tests for SNS routes."""

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from src.adapters.web.server import app
from src.adapters.sns.x import XPostResult
from src.adapters.sns.threads import ThreadsPostResult


@pytest.fixture
def transport():
    return ASGITransport(app=app)


class TestXRoutes:
    @pytest.mark.asyncio
    async def test_x_post_unconfigured(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/sns/x/post", json={"text": "hi"})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_x_post_success(self, transport):
        result = XPostResult(success=True, post_id="1", text="hi")
        with patch("src.adapters.web.sns_routes.x_client") as mock:
            mock.is_configured = True
            mock.post = AsyncMock(return_value=result)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/sns/x/post", json={"text": "hi"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["post_id"] == "1"

    @pytest.mark.asyncio
    async def test_x_reply_unconfigured(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/sns/x/reply", json={"text": "hi", "post_id": "1"})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_x_reply_success(self, transport):
        result = XPostResult(success=True, post_id="2", text="reply")
        with patch("src.adapters.web.sns_routes.x_client") as mock:
            mock.is_configured = True
            mock.reply = AsyncMock(return_value=result)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/sns/x/reply", json={"text": "reply", "post_id": "1"})
        assert resp.status_code == 200
        assert resp.json()["post_id"] == "2"


class TestThreadsRoutes:
    @pytest.mark.asyncio
    async def test_threads_post_unconfigured(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/sns/threads/post", json={"text": "hi"})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_threads_post_success(self, transport):
        result = ThreadsPostResult(success=True, post_id="t1", text="hi")
        with patch("src.adapters.web.sns_routes.threads_client") as mock:
            mock.is_configured = True
            mock.post = AsyncMock(return_value=result)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/sns/threads/post", json={"text": "hi"})
        assert resp.status_code == 200
        assert resp.json()["post_id"] == "t1"

    @pytest.mark.asyncio
    async def test_threads_reply_unconfigured(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/sns/threads/reply", json={"text": "hi", "post_id": "1"})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_threads_reply_success(self, transport):
        result = ThreadsPostResult(success=True, post_id="tr1", text="reply")
        with patch("src.adapters.web.sns_routes.threads_client") as mock:
            mock.is_configured = True
            mock.reply = AsyncMock(return_value=result)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/sns/threads/reply", json={"text": "reply", "post_id": "t1"})
        assert resp.status_code == 200
        assert resp.json()["post_id"] == "tr1"


class TestValidation:
    @pytest.mark.asyncio
    async def test_missing_text(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/sns/x/post", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_reply_missing_post_id(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/sns/threads/reply", json={"text": "hi"})
        assert resp.status_code == 422
