"""Configuration and shared state."""

__version__ = "0.0.4"

import os
import sys
import uuid

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
    # Keep legacy alias keys across providers for compatibility with:
    # - existing `!model <alias>` Discord command usage
    # - hormone logic (`sonnet`/`haiku`) and persisted config defaults.
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
    "check_interval": 30 * 60,  # 30 minutes in seconds
    "autonomous_mode": True,
    "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", ""),
    # X (Twitter)
    "x_consumer_key": os.getenv("X_CONSUMER_KEY", ""),
    "x_consumer_secret": os.getenv("X_CONSUMER_SECRET", ""),
    "x_access_token": os.getenv("X_ACCESS_TOKEN", ""),
    "x_access_token_secret": os.getenv("X_ACCESS_TOKEN_SECRET", ""),
    # Threads (Meta)
    "threads_user_id": os.getenv("THREADS_USER_ID", ""),
    "threads_access_token": os.getenv("THREADS_ACCESS_TOKEN", ""),
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
