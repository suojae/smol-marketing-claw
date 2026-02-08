"""Usage tracking and rate limiting."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from src.config import CONFIG


class UsageLimitExceeded(Exception):
    """Raised when a usage limit is exceeded"""
    pass


class UsageTracker:
    """Tracks Claude CLI call usage and enforces rate limits"""

    def __init__(self, usage_file: str = "memory/usage.json"):
        self.usage_file = Path(usage_file)
        self.usage_file.parent.mkdir(exist_ok=True)
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load usage data from file"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"calls": [], "total_calls": 0}

    def _save(self):
        """Persist usage data to file"""
        try:
            with open(self.usage_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save usage data: {e}")

    def _calls_since(self, seconds: float) -> int:
        """Count calls within the last N seconds"""
        cutoff = (datetime.now() - timedelta(seconds=seconds)).isoformat()
        return sum(1 for ts in self._data["calls"] if ts > cutoff)

    def _cleanup_old_calls(self):
        """Remove call timestamps older than 24 hours"""
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        self._data["calls"] = [ts for ts in self._data["calls"] if ts > cutoff]

    def check_limits(self):
        """Check all usage limits before a call. Raises UsageLimitExceeded if any limit is hit."""
        limits = CONFIG["usage_limits"]

        # Check if paused
        if limits.get("paused", False):
            raise UsageLimitExceeded("Usage is paused by configuration")

        # Check minimum interval (cooldown)
        min_interval = limits["min_call_interval_seconds"]
        if self._data["calls"]:
            last_call = self._data["calls"][-1]
            elapsed = (datetime.now() - datetime.fromisoformat(last_call)).total_seconds()
            if elapsed < min_interval:
                raise UsageLimitExceeded(
                    f"Cooldown: {min_interval - elapsed:.1f}s remaining "
                    f"(min interval: {min_interval}s)"
                )

        # Check per-minute limit
        per_minute = self._calls_since(60)
        if per_minute >= limits["max_calls_per_minute"]:
            raise UsageLimitExceeded(
                f"Per-minute limit reached: {per_minute}/{limits['max_calls_per_minute']}"
            )

        # Check per-hour limit
        per_hour = self._calls_since(3600)
        if per_hour >= limits["max_calls_per_hour"]:
            raise UsageLimitExceeded(
                f"Per-hour limit reached: {per_hour}/{limits['max_calls_per_hour']}"
            )

        # Check daily limit
        per_day = self._calls_since(86400)
        if per_day >= limits["max_calls_per_day"]:
            raise UsageLimitExceeded(
                f"Daily limit reached: {per_day}/{limits['max_calls_per_day']}"
            )

    def record_call(self):
        """Record a successful call"""
        self._cleanup_old_calls()
        self._data["calls"].append(datetime.now().isoformat())
        self._data["total_calls"] = self._data.get("total_calls", 0) + 1
        self._save()

    def get_warning(self) -> Optional[str]:
        """Return a warning message if daily usage exceeds the threshold percentage"""
        limits = CONFIG["usage_limits"]
        per_day = self._calls_since(86400)
        threshold = limits["max_calls_per_day"] * limits["warning_threshold_pct"] / 100

        if per_day >= threshold:
            return (
                f"Usage warning: {per_day}/{limits['max_calls_per_day']} "
                f"daily calls used ({per_day * 100 // limits['max_calls_per_day']}%)"
            )
        return None

    def get_status(self) -> Dict[str, Any]:
        """Return current usage stats for the /status endpoint"""
        limits = CONFIG["usage_limits"]
        per_minute = self._calls_since(60)
        per_hour = self._calls_since(3600)
        per_day = self._calls_since(86400)

        return {
            "calls_today": per_day,
            "calls_this_hour": per_hour,
            "calls_this_minute": per_minute,
            "limits": {
                "per_minute": limits["max_calls_per_minute"],
                "per_hour": limits["max_calls_per_hour"],
                "per_day": limits["max_calls_per_day"],
            },
            "paused": limits.get("paused", False),
            "total_calls_all_time": self._data.get("total_calls", 0),
        }
