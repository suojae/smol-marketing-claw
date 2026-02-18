"""X (Twitter) adapter — re-exports XClient as SNSPort implementation."""

from src.x_client import XClient, XPostResult

__all__ = ["XClient", "XPostResult"]
