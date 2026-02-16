"""Instagram client using Meta Graph API (aiohttp-based)."""

from dataclasses import dataclass
from typing import Optional

import aiohttp

from src.config import CONFIG

INSTAGRAM_API_BASE = "https://graph.facebook.com/v21.0"


@dataclass
class InstagramPostResult:
    success: bool
    post_id: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None


class InstagramClient:
    """Async Instagram Graph API client (2-step: create container -> publish).

    Instagram requires an image for every post.
    """

    @property
    def is_configured(self) -> bool:
        return bool(CONFIG["instagram_user_id"] and CONFIG["instagram_access_token"])

    @staticmethod
    def truncate_text(text: str, limit: int = 2200) -> str:
        """Instagram caption limit is ~2200 characters."""
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    async def _create_container(
        self,
        caption: str,
        image_url: str,
    ) -> str:
        """Create a media container for an image post."""
        user_id = CONFIG["instagram_user_id"]
        token = CONFIG["instagram_access_token"]
        url = f"{INSTAGRAM_API_BASE}/{user_id}/media"
        params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as resp:
                data = await resp.json()
                if "id" not in data:
                    raise RuntimeError(data.get("error", {}).get("message", str(data)))
                return data["id"]

    async def _publish(self, container_id: str) -> str:
        """Publish a media container."""
        user_id = CONFIG["instagram_user_id"]
        token = CONFIG["instagram_access_token"]
        url = f"{INSTAGRAM_API_BASE}/{user_id}/media_publish"
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

    async def post(self, text: str, image_url: str) -> InstagramPostResult:
        """Post an image with caption to Instagram.

        Args:
            text: Caption text.
            image_url: Public URL of the image.
        """
        text = self.truncate_text(text)
        if not image_url:
            return InstagramPostResult(
                success=False, text=text, error="Instagram requires an image_url."
            )
        try:
            container_id = await self._create_container(text, image_url)
            post_id = await self._publish(container_id)
            return InstagramPostResult(success=True, post_id=post_id, text=text)
        except Exception as e:
            return InstagramPostResult(success=False, text=text, error=str(e))
