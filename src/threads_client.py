"""Threads (Meta) client using aiohttp."""

from dataclasses import dataclass
from typing import Optional

import aiohttp

from src.config import CONFIG

THREADS_API_BASE = "https://graph.threads.net/v1.0"


@dataclass
class ThreadsPostResult:
    success: bool
    post_id: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None


class ThreadsClient:
    """Async Threads API client (2-step: create container → publish)."""

    @property
    def is_configured(self) -> bool:
        return bool(CONFIG["threads_user_id"] and CONFIG["threads_access_token"])

    @staticmethod
    def truncate_text(text: str, limit: int = 500) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    async def _create_container(
        self,
        text: str,
        reply_to_id: Optional[str] = None,
    ) -> str:
        user_id = CONFIG["threads_user_id"]
        token = CONFIG["threads_access_token"]
        url = f"{THREADS_API_BASE}/{user_id}/threads"
        params = {
            "media_type": "TEXT",
            "text": text,
            "access_token": token,
        }
        if reply_to_id:
            params["reply_to_id"] = reply_to_id

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as resp:
                data = await resp.json()
                if "id" not in data:
                    raise RuntimeError(data.get("error", {}).get("message", str(data)))
                return data["id"]

    async def _publish(self, container_id: str) -> str:
        user_id = CONFIG["threads_user_id"]
        token = CONFIG["threads_access_token"]
        url = f"{THREADS_API_BASE}/{user_id}/threads_publish"
        params = {
            "creation_id": container_id,
            "access_token": token,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as resp:
                data = await resp.json()
                if "id" not in data:
                    raise RuntimeError(data.get("error", {}).get("message", str(data)))
                return data["id"]

    async def post(self, text: str) -> ThreadsPostResult:
        text = self.truncate_text(text)
        try:
            container_id = await self._create_container(text)
            post_id = await self._publish(container_id)
            return ThreadsPostResult(success=True, post_id=post_id, text=text)
        except Exception as e:
            return ThreadsPostResult(success=False, text=text, error=str(e))

    async def reply(self, text: str, post_id: str) -> ThreadsPostResult:
        text = self.truncate_text(text)
        try:
            container_id = await self._create_container(text, reply_to_id=post_id)
            new_id = await self._publish(container_id)
            return ThreadsPostResult(success=True, post_id=new_id, text=text)
        except Exception as e:
            return ThreadsPostResult(success=False, text=text, error=str(e))
