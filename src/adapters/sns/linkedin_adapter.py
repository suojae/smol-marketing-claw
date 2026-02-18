"""LinkedIn adapter — re-exports LinkedInClient as SNSPort implementation."""

from src.linkedin_client import LinkedInClient, LinkedInPostResult

__all__ = ["LinkedInClient", "LinkedInPostResult"]
