"""News client — X Search API-based keyword monitoring."""

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


class NewsClient:
    """Search X (Twitter) for trending news and keyword monitoring."""

    @property
    def is_configured(self) -> bool:
        return bool(CONFIG["news_x_bearer_token"])

    async def search(self, keyword: str, limit: int = 10) -> NewsSearchResult:
        """Search recent tweets for a keyword.

        Args:
            keyword: Search query.
            limit: Max results (10-100).
        """
        bearer = CONFIG["news_x_bearer_token"]
        if not bearer:
            return NewsSearchResult(
                success=False,
                error="NEWS_X_BEARER_TOKEN not configured.",
            )

        limit = max(10, min(100, limit))

        headers = {"Authorization": f"Bearer {bearer}"}
        params = {
            "query": f"{keyword} -is:retweet lang:ko OR lang:en",
            "max_results": str(limit),
            "tweet.fields": "created_at,author_id,text",
            "expansions": "author_id",
            "user.fields": "username",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    X_SEARCH_API, headers=headers, params=params
                ) as resp:
                    data = await resp.json()

                    if resp.status >= 400:
                        error_msg = data.get("detail", data.get("title", str(data)))
                        return NewsSearchResult(success=False, error=error_msg)

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
            return NewsSearchResult(success=False, error=str(e))
