"""News client — X Search API-based keyword monitoring."""

import asyncio
import sys
from dataclasses import dataclass, field
from typing import Optional, List

import aiohttp

from src.config import CONFIG

X_SEARCH_API = "https://api.twitter.com/2/tweets/search/recent"


@dataclass
class NewsItem:
    text: str
    author: str = ""
    created_at: str = ""
    tweet_id: str = ""
    url: str = ""


@dataclass
class NewsSearchResult:
    success: bool
    items: List[NewsItem] = field(default_factory=list)
    error: Optional[str] = None


import re

# X Search operators that could alter query semantics
_OPERATOR_PATTERN = re.compile(
    r"\b(from|to|is|has|lang|url|retweets_of|context|entity|"
    r"conversation_id|bio|bio_name|bio_location|place|place_country|"
    r"point_radius|bounding_box|sample)\s*:",
    re.IGNORECASE,
)


class NewsClient:
    """Search X (Twitter) for trending news and keyword monitoring."""

    @property
    def is_configured(self) -> bool:
        return bool(CONFIG["news_x_bearer_token"])

    @staticmethod
    def _sanitize_keyword(keyword: str) -> str:
        """Whitelist-based sanitization: allow only safe characters."""
        # Strip zero-width characters
        sanitized = re.sub(r"[\u200b-\u200f\u2028-\u202f\ufeff]", "", keyword)
        # Allow alphanumeric, spaces, basic CJK, and common punctuation only
        sanitized = re.sub(r"[^\w\s\u3000-\u9fff\uac00-\ud7af.,!?#@\-]", " ", sanitized)
        # Remove X Search operators
        sanitized = _OPERATOR_PATTERN.sub("", sanitized)
        sanitized = re.sub(r"\b(OR|AND)\b", " ", sanitized)
        return " ".join(sanitized.split()).strip()

    async def search(self, keyword: str, limit: int = 10) -> NewsSearchResult:
        """Search recent tweets for a keyword.

        Args:
            keyword: Search query (operators are stripped for safety).
            limit: Max results (10-100).
        """
        bearer = CONFIG["news_x_bearer_token"]
        if not bearer:
            return NewsSearchResult(
                success=False,
                error="NEWS_X_BEARER_TOKEN not configured.",
            )

        safe_keyword = self._sanitize_keyword(keyword)
        if not safe_keyword:
            return NewsSearchResult(
                success=False,
                error="Keyword is empty after sanitization.",
            )

        limit = max(10, min(100, limit))

        headers = {"Authorization": f"Bearer {bearer}"}
        params = {
            "query": f"{safe_keyword} -is:retweet lang:ko OR lang:en",
            "max_results": str(limit),
            "tweet.fields": "created_at,author_id,text",
            "expansions": "author_id",
            "user.fields": "username",
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        X_SEARCH_API, headers=headers, params=params
                    ) as resp:
                        if resp.status == 429:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(min(2 ** attempt, 30))
                                continue
                            return NewsSearchResult(success=False, error="Rate limited (429)")

                        if resp.status >= 400:
                            body = await resp.text()
                            return NewsSearchResult(
                                success=False, error=f"HTTP {resp.status}: {body}"
                            )

                        data = await resp.json()
                        tweets = data.get("data", [])
                        users = {}
                        if "includes" in data and "users" in data["includes"]:
                            for u in data["includes"]["users"]:
                                users[u["id"]] = u.get("username", "")

                        items = []
                        for t in tweets:
                            author_id = t.get("author_id", "")
                            username = users.get(author_id, "")
                            tweet_id = t.get("id", "")
                            items.append(
                                NewsItem(
                                    text=t.get("text", ""),
                                    author=username,
                                    created_at=t.get("created_at", ""),
                                    tweet_id=tweet_id,
                                    url=f"https://x.com/{username}/status/{tweet_id}" if username else "",
                                )
                            )

                        return NewsSearchResult(success=True, items=items)

            except Exception as e:
                if attempt == max_retries - 1:
                    return NewsSearchResult(success=False, error=str(e))
                await asyncio.sleep(min(2 ** attempt, 30))

        return NewsSearchResult(success=False, error="Max retries exceeded")
