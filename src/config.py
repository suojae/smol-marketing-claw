"""Configuration and shared state."""

__version__ = "0.1.0"

import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Dict

from dotenv import load_dotenv

load_dotenv()

_stderr_print = lambda *a, **kw: print(*a, **kw, file=sys.stderr)

SUPPORTED_AI_PROVIDERS = ("claude", "codex")
AI_PROVIDER = os.getenv("AI_PROVIDER", "claude").strip().lower()
if AI_PROVIDER not in SUPPORTED_AI_PROVIDERS:
    _stderr_print(f"Unsupported AI_PROVIDER={AI_PROVIDER!r}, falling back to 'claude'")
    AI_PROVIDER = "claude"

MODEL_ALIASES_BY_PROVIDER = {
    "claude": {
        "opus": os.getenv("CLAUDE_MODEL_OPUS", "claude-opus-4-6"),
        "sonnet": os.getenv("CLAUDE_MODEL_SONNET", "claude-sonnet-4-5-20250929"),
        "haiku": os.getenv("CLAUDE_MODEL_HAIKU", "claude-haiku-4-5-20251001"),
    },
    "codex": {
        "opus": os.getenv("CODEX_MODEL_OPUS", "gpt-5.3-codex"),
        "sonnet": os.getenv("CODEX_MODEL_SONNET", "gpt-5.3-codex"),
        "haiku": os.getenv("CODEX_MODEL_HAIKU", "gpt-5.3-codex-mini"),
    },
}

MODEL_ALIASES = MODEL_ALIASES_BY_PROVIDER[AI_PROVIDER]

DEFAULT_MODEL = os.getenv("AI_DEFAULT_MODEL", "sonnet").strip().lower()
if DEFAULT_MODEL not in MODEL_ALIASES:
    fallback = "sonnet" if "sonnet" in MODEL_ALIASES else next(iter(MODEL_ALIASES))
    _stderr_print(
        f"Unsupported AI_DEFAULT_MODEL={DEFAULT_MODEL!r} for provider={AI_PROVIDER!r}, "
        f"falling back to {fallback!r}"
    )
    DEFAULT_MODEL = fallback

CONFIG = {
    "port": 3000,
    "session_id": str(uuid.uuid4()),
    "ai_provider": AI_PROVIDER,
    # X (Twitter)
    "x_consumer_key": os.getenv("X_CONSUMER_KEY", ""),
    "x_consumer_secret": os.getenv("X_CONSUMER_SECRET", ""),
    "x_access_token": os.getenv("X_ACCESS_TOKEN", ""),
    "x_access_token_secret": os.getenv("X_ACCESS_TOKEN_SECRET", ""),
    # Threads (Meta)
    "threads_user_id": os.getenv("THREADS_USER_ID", ""),
    "threads_access_token": os.getenv("THREADS_ACCESS_TOKEN", ""),
    # Instagram (Meta Graph API)
    "instagram_user_id": os.getenv("INSTAGRAM_USER_ID", ""),
    "instagram_access_token": os.getenv("INSTAGRAM_ACCESS_TOKEN", ""),
    # Usage limits
    "usage_limits": {
        "max_calls_per_minute": 60,
        "max_calls_per_hour": 500,
        "max_calls_per_day": 10000,
        "min_call_interval_seconds": 1,
        "warning_threshold_pct": 80,
        "paused": False,
    },
    # Posting guardrail — require explicit human approval before publishing
    # Set REQUIRE_MANUAL_APPROVAL=false to bypass (not recommended)
    "require_manual_approval": os.getenv("REQUIRE_MANUAL_APPROVAL", "true").strip().lower()
    in ("1", "true", "yes", "on"),
}

def _int_env(key: str) -> int:
    val = os.getenv(key, "").strip()
    return int(val) if val else 0

# Discord multi-bot channel IDs
DISCORD_CHANNELS = {
    "team": _int_env("DISCORD_TEAM_CHANNEL_ID"),
    "test": _int_env("DISCORD_TEST_CHANNEL_ID"),
    "threads": _int_env("DISCORD_THREADS_CHANNEL_ID"),
    "instagram": _int_env("DISCORD_INSTAGRAM_CHANNEL_ID"),
    "hr": _int_env("DISCORD_HR_CHANNEL_ID"),
}

# Discord multi-bot tokens
DISCORD_TOKENS = {
    "threads": os.getenv("DISCORD_THREADS_TOKEN", ""),
    "instagram": os.getenv("DISCORD_INSTAGRAM_TOKEN", ""),
    "hr": os.getenv("DISCORD_HR_TOKEN", ""),
}


# ── Typed config (new) ──────────────────────────────────────


@dataclass
class UsageLimitsConfig:
    max_calls_per_minute: int = 60
    max_calls_per_hour: int = 500
    max_calls_per_day: int = 10000
    min_call_interval_seconds: int = 1
    warning_threshold_pct: int = 80
    paused: bool = False


@dataclass
class SNSConfig:
    x_consumer_key: str = ""
    x_consumer_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""
    threads_user_id: str = ""
    threads_access_token: str = ""
    instagram_user_id: str = ""
    instagram_access_token: str = ""


@dataclass
class DiscordConfig:
    channels: Dict[str, int] = field(default_factory=dict)
    tokens: Dict[str, str] = field(default_factory=dict)


@dataclass
class AppConfig:
    """Typed configuration — replaces CONFIG dict for new code."""

    port: int = 3000
    session_id: str = ""
    ai_provider: str = "claude"
    default_model: str = "sonnet"
    require_manual_approval: bool = True
    sns: SNSConfig = field(default_factory=SNSConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    usage_limits: UsageLimitsConfig = field(default_factory=UsageLimitsConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create AppConfig from environment variables."""
        return cls(
            port=int(os.getenv("PORT", "3000")),
            session_id=CONFIG["session_id"],
            ai_provider=AI_PROVIDER,
            default_model=DEFAULT_MODEL,
            require_manual_approval=CONFIG["require_manual_approval"],
            sns=SNSConfig(
                x_consumer_key=CONFIG["x_consumer_key"],
                x_consumer_secret=CONFIG["x_consumer_secret"],
                x_access_token=CONFIG["x_access_token"],
                x_access_token_secret=CONFIG["x_access_token_secret"],
                threads_user_id=CONFIG["threads_user_id"],
                threads_access_token=CONFIG["threads_access_token"],
                instagram_user_id=CONFIG["instagram_user_id"],
                instagram_access_token=CONFIG["instagram_access_token"],
            ),
            discord=DiscordConfig(
                channels=dict(DISCORD_CHANNELS),
                tokens=dict(DISCORD_TOKENS),
            ),
            usage_limits=UsageLimitsConfig(**CONFIG["usage_limits"]),
        )
