"""LinkedIn client using aiohttp (OAuth 2.0 + REST API v2)."""

from dataclasses import dataclass
from typing import Optional

import aiohttp

from src.config import CONFIG

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


@dataclass
class LinkedInPostResult:
    success: bool
    post_id: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None


class LinkedInClient:
    """Async LinkedIn API client for posting text content."""

    @property
    def is_configured(self) -> bool:
        return bool(CONFIG["linkedin_access_token"])

    @staticmethod
    def truncate_text(text: str, limit: int = 3000) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    async def _get_user_urn(self, session: aiohttp.ClientSession) -> str:
        """Get the authenticated user's URN (person ID)."""
        headers = {
            "Authorization": f"Bearer {CONFIG['linkedin_access_token']}",
        }
        async with session.get(f"{LINKEDIN_API_BASE}/userinfo", headers=headers) as resp:
            if resp.status >= 400:
                body = await resp.text()
                raise RuntimeError(f"LinkedIn auth failed (HTTP {resp.status}): {body}")
            data = await resp.json()
            if "sub" not in data:
                raise RuntimeError(f"Failed to get user info: {data}")
            return f"urn:li:person:{data['sub']}"

    async def post(self, text: str) -> LinkedInPostResult:
        """Create a text post on LinkedIn."""
        text = self.truncate_text(text)
        token = CONFIG["linkedin_access_token"]

        try:
            async with aiohttp.ClientSession() as session:
                author_urn = await self._get_user_urn(session)

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                }

                payload = {
                    "author": author_urn,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": text},
                            "shareMediaCategory": "NONE",
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    },
                }

                async with session.post(
                    f"{LINKEDIN_API_BASE}/ugcPosts",
                    headers=headers,
                    json=payload,
                ) as resp:
                    data = await resp.json()
                    if resp.status >= 400:
                        error_msg = data.get("message", str(data))
                        return LinkedInPostResult(success=False, text=text, error=error_msg)

                    post_id = data.get("id", "")
                    return LinkedInPostResult(success=True, post_id=post_id, text=text)

        except Exception as e:
            return LinkedInPostResult(success=False, text=text, error=str(e))
