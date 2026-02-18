"""Global state for MCP server — initializes all subsystems."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from src.config import CONFIG
from src.infrastructure.usage import UsageTracker
from src.infrastructure.memory import GuardrailMemory
from src.infrastructure.context import ContextCollector
from src.adapters.sns.x import XClient
from src.adapters.sns.threads import ThreadsClient

# Resolve memory directory relative to plugin root
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = PLUGIN_ROOT.parent / "memory"
MEMORY_DIR.mkdir(exist_ok=True)


def _log(msg: str):
    print(msg, file=sys.stderr)


class AppState:
    """Singleton-ish state container for all subsystems."""

    def __init__(self):
        _log("Initializing Smol Claw MCP state...")

        # Usage tracker (core — must succeed)
        self.usage_tracker = UsageTracker(
            usage_file=str(MEMORY_DIR / "usage.json"),
            limits=CONFIG["usage_limits"],
        )

        # Decision memory
        self.memory = GuardrailMemory(memory_dir=str(MEMORY_DIR))

        # Context collector
        self.context_collector = ContextCollector()

        # SNS clients (optional — graceful degradation)
        try:
            self.x_client = XClient()
        except Exception as e:
            _log(f"XClient init failed: {e}")
            self.x_client = None

        try:
            self.threads_client = ThreadsClient()
        except Exception as e:
            _log(f"ThreadsClient init failed: {e}")
            self.threads_client = None

        try:
            from src.adapters.sns.linkedin import LinkedInClient
            self.linkedin_client = LinkedInClient()
        except Exception as e:
            _log(f"LinkedInClient init failed: {e}")
            self.linkedin_client = None

        try:
            from src.adapters.sns.instagram import InstagramClient
            self.instagram_client = InstagramClient()
        except Exception as e:
            _log(f"InstagramClient init failed: {e}")
            self.instagram_client = None

        try:
            from src.adapters.sns.news import NewsClient
            self.news_client = NewsClient()
        except Exception as e:
            _log(f"NewsClient init failed: {e}")
            self.news_client = None

        _log("Smol Claw MCP state initialized.")


# Module-level singleton
_state: Optional[AppState] = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state
