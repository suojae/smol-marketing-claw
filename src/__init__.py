"""Smol Claw — Multi-Agent Marketing System package."""

from src.config import CONFIG, MODEL_ALIASES, DEFAULT_MODEL, DISCORD_CHANNELS, DISCORD_TOKENS
from src.infrastructure.context import ContextCollector
from src.infrastructure.usage import UsageLimitExceeded, UsageTracker
from src.infrastructure.memory import SimpleMemory, GuardrailMemory
from src.domain.persona import BOT_PERSONA
from src.adapters.sns.x import XClient, XPostResult
from src.adapters.sns.threads import ThreadsClient, ThreadsPostResult
from src.adapters.sns.instagram import InstagramClient, InstagramPostResult

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
    "InstagramClient",
    "InstagramPostResult",
]
