"""X (Twitter) client using tweepy."""

import asyncio
from dataclasses import dataclass
from typing import Optional

import tweepy

from src.config import CONFIG


@dataclass
class XPostResult:
    success: bool
    post_id: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None


class XClient:
    """Async wrapper around tweepy.Client for X/Twitter API v2."""

    def __init__(self):
        self._client: Optional[tweepy.Client] = None

    @property
    def is_configured(self) -> bool:
        keys = [
            CONFIG["x_consumer_key"],
            CONFIG["x_consumer_secret"],
            CONFIG["x_access_token"],
            CONFIG["x_access_token_secret"],
        ]
        return all(k for k in keys)

    def _get_client(self) -> tweepy.Client:
        if self._client is None:
            self._client = tweepy.Client(
                consumer_key=CONFIG["x_consumer_key"],
                consumer_secret=CONFIG["x_consumer_secret"],
                access_token=CONFIG["x_access_token"],
                access_token_secret=CONFIG["x_access_token_secret"],
            )
        return self._client

    @staticmethod
    def truncate_text(text: str, limit: int = 280) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    async def post(self, text: str) -> XPostResult:
        text = self.truncate_text(text)
        try:
            client = self._get_client()
            response = await asyncio.to_thread(client.create_tweet, text=text)
            tweet_id = str(response.data["id"])
            return XPostResult(success=True, post_id=tweet_id, text=text)
        except Exception as e:
            return XPostResult(success=False, text=text, error=str(e))

    async def reply(self, text: str, tweet_id: str) -> XPostResult:
        text = self.truncate_text(text)
        try:
            client = self._get_client()
            response = await asyncio.to_thread(
                client.create_tweet,
                text=text,
                in_reply_to_tweet_id=tweet_id,
            )
            new_id = str(response.data["id"])
            return XPostResult(success=True, post_id=new_id, text=text)
        except Exception as e:
            return XPostResult(success=False, text=text, error=str(e))
