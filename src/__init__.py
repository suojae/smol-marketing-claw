"""Smol Claw — Multi-Agent Marketing System package."""

from src.config import CONFIG, MODEL_ALIASES, DEFAULT_MODEL, DISCORD_CHANNELS, DISCORD_TOKENS
from src.context import ContextCollector
from src.usage import UsageLimitExceeded, UsageTracker
from src.memory import SimpleMemory, GuardrailMemory
from src.persona import BOT_PERSONA
from src.x_client import XClient, XPostResult
from src.threads_client import ThreadsClient, ThreadsPostResult
from src.linkedin_client import LinkedInClient, LinkedInPostResult
from src.instagram_client import InstagramClient, InstagramPostResult
from src.news_client import NewsClient, NewsItem, NewsSearchResult

__all__ = [
    "CONFIG",
    "MODEL_ALIASES",
    "DEFAULT_MODEL",
    "DISCORD_CHANNELS",
    "DISCORD_TOKENS",
    "ContextCollector",
    "UsageLimitExceeded",
    "UsageTracker",
    "SimpleMemory",
    "GuardrailMemory",
    "BOT_PERSONA",
    "XClient",
    "XPostResult",
    "ThreadsClient",
    "ThreadsPostResult",
    "LinkedInClient",
    "LinkedInPostResult",
    "InstagramClient",
    "InstagramPostResult",
    "NewsClient",
    "NewsItem",
    "NewsSearchResult",
]
