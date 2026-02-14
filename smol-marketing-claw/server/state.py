"""Global state for MCP server — initializes all subsystems."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from src.config import CONFIG
from src.usage import UsageTracker
from src.hormones import DigitalHormones
from src.hormone_memory import HormoneMemory
from src.memory import GuardrailMemory
from src.context import ContextCollector
from src.x_client import XClient
from src.threads_client import ThreadsClient

# Resolve memory directory relative to plugin root
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parent.parent))
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

        # Hormone system (core — must succeed)
        self.hormones = DigitalHormones(
            state_file=str(MEMORY_DIR / "hormones.json"),
            usage_tracker=self.usage_tracker,
        )

        # Hormone vector memory (optional — graceful degradation)
        try:
            self.hormone_memory = HormoneMemory(persist_dir=str(MEMORY_DIR / "chroma"))
        except Exception as e:
            _log(f"HormoneMemory init failed (degraded mode): {e}")
            self.hormone_memory = None

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

        # Discord bot (lazy-initialized via discord_control tool)
        self.discord_bot = None
        self._discord_task = None
        self._hormones_mtime = 0.0

        _log("Smol Claw MCP state initialized.")

    def reload_hormones_if_stale(self):
        """Reload hormone state from disk if externally modified (e.g. by hooks)."""
        state_file = self.hormones.state_file
        if not state_file.exists():
            return
        try:
            mtime = state_file.stat().st_mtime
            if mtime > self._hormones_mtime:
                self.hormones.state = self.hormones._load_state()
                self._hormones_mtime = mtime
        except Exception:
            pass


# Module-level singleton
_state: Optional[AppState] = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state
