"""Instagram adapter — re-exports InstagramClient as SNSPort implementation."""

from src.instagram_client import InstagramClient, InstagramPostResult, RateLimitError

__all__ = ["InstagramClient", "InstagramPostResult", "RateLimitError"]
