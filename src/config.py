"""Configuration and shared state."""

__version__ = "0.0.3"

import asyncio
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

MODEL_ALIASES = {
    "opus":   "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku":  "claude-haiku-4-5-20251001",
}
DEFAULT_MODEL = "sonnet"

CONFIG = {
    "port": 3000,
    "session_id": str(uuid.uuid4()),
    "check_interval": 30 * 60,  # 30 minutes in seconds
    "autonomous_mode": True,
    "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", ""),  # Set via environment variable
    # X (Twitter)
    "x_consumer_key": os.getenv("X_CONSUMER_KEY", ""),
    "x_consumer_secret": os.getenv("X_CONSUMER_SECRET", ""),
    "x_access_token": os.getenv("X_ACCESS_TOKEN", ""),
    "x_access_token_secret": os.getenv("X_ACCESS_TOKEN_SECRET", ""),
    # Threads (Meta)
    "threads_user_id": os.getenv("THREADS_USER_ID", ""),
    "threads_access_token": os.getenv("THREADS_ACCESS_TOKEN", ""),
    "usage_limits": {
        "max_calls_per_minute": 5,
        "max_calls_per_hour": 20,
        "max_calls_per_day": 500,
        "min_call_interval_seconds": 5,
        "warning_threshold_pct": 80,
        "paused": False,
    },
}

# Global event queue — re-created in startup_event() to match uvicorn's loop
event_queue: asyncio.Queue = asyncio.Queue()
