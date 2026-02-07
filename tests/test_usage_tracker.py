"""Tests for UsageTracker"""

import json
import sys
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from importlib import import_module

# Import from the server module (hyphenated filename)
import importlib.util

spec = importlib.util.spec_from_file_location(
    "server", os.path.join(os.path.dirname(os.path.dirname(__file__)), "autonomous-ai-server.py")
)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

UsageTracker = server.UsageTracker
UsageLimitExceeded = server.UsageLimitExceeded
CONFIG = server.CONFIG


@pytest.fixture
def tracker(tmp_path):
    """Create a UsageTracker with a temporary usage file"""
    usage_file = tmp_path / "usage.json"
    t = UsageTracker(usage_file=str(usage_file))
    return t


@pytest.fixture(autouse=True)
def reset_config():
    """Reset CONFIG usage_limits before each test"""
    original = CONFIG["usage_limits"].copy()
    yield
    CONFIG["usage_limits"] = original


class TestDailyLimit:
    def test_blocks_when_daily_limit_reached(self, tracker):
        """Should raise UsageLimitExceeded when daily call limit is reached"""
        CONFIG["usage_limits"]["max_calls_per_day"] = 3
        CONFIG["usage_limits"]["min_call_interval_seconds"] = 0
        CONFIG["usage_limits"]["max_calls_per_minute"] = 999
        CONFIG["usage_limits"]["max_calls_per_hour"] = 999

        for _ in range(3):
            tracker.record_call()

        with pytest.raises(UsageLimitExceeded, match="Daily limit"):
            tracker.check_limits()

    def test_allows_under_daily_limit(self, tracker):
        """Should not raise when under the daily limit"""
        CONFIG["usage_limits"]["max_calls_per_day"] = 5
        CONFIG["usage_limits"]["min_call_interval_seconds"] = 0
        CONFIG["usage_limits"]["max_calls_per_minute"] = 999
        CONFIG["usage_limits"]["max_calls_per_hour"] = 999

        for _ in range(4):
            tracker.record_call()

        # Should not raise
        tracker.check_limits()


class TestPerMinuteLimit:
    def test_blocks_when_per_minute_limit_reached(self, tracker):
        """Should raise UsageLimitExceeded when per-minute limit is reached"""
        CONFIG["usage_limits"]["max_calls_per_minute"] = 2
        CONFIG["usage_limits"]["min_call_interval_seconds"] = 0
        CONFIG["usage_limits"]["max_calls_per_hour"] = 999
        CONFIG["usage_limits"]["max_calls_per_day"] = 999

        for _ in range(2):
            tracker.record_call()

        with pytest.raises(UsageLimitExceeded, match="Per-minute limit"):
            tracker.check_limits()


class TestCooldown:
    def test_blocks_during_cooldown(self, tracker):
        """Should raise UsageLimitExceeded during cooldown period"""
        CONFIG["usage_limits"]["min_call_interval_seconds"] = 10
        CONFIG["usage_limits"]["max_calls_per_minute"] = 999
        CONFIG["usage_limits"]["max_calls_per_hour"] = 999
        CONFIG["usage_limits"]["max_calls_per_day"] = 999

        tracker.record_call()

        with pytest.raises(UsageLimitExceeded, match="Cooldown"):
            tracker.check_limits()

    def test_allows_after_cooldown(self, tracker):
        """Should allow calls after cooldown period has elapsed"""
        CONFIG["usage_limits"]["min_call_interval_seconds"] = 1
        CONFIG["usage_limits"]["max_calls_per_minute"] = 999
        CONFIG["usage_limits"]["max_calls_per_hour"] = 999
        CONFIG["usage_limits"]["max_calls_per_day"] = 999

        # Manually insert a call timestamp in the past
        past_time = (datetime.now() - timedelta(seconds=5)).isoformat()
        tracker._data["calls"].append(past_time)

        # Should not raise
        tracker.check_limits()


class TestPause:
    def test_blocks_when_paused(self, tracker):
        """Should raise UsageLimitExceeded when paused"""
        CONFIG["usage_limits"]["paused"] = True

        with pytest.raises(UsageLimitExceeded, match="paused"):
            tracker.check_limits()

    def test_allows_when_not_paused(self, tracker):
        """Should allow calls when not paused"""
        CONFIG["usage_limits"]["paused"] = False
        CONFIG["usage_limits"]["min_call_interval_seconds"] = 0

        # Should not raise
        tracker.check_limits()


class TestWarning:
    def test_returns_warning_at_threshold(self, tracker):
        """Should return warning when daily usage hits threshold"""
        CONFIG["usage_limits"]["max_calls_per_day"] = 10
        CONFIG["usage_limits"]["warning_threshold_pct"] = 80
        CONFIG["usage_limits"]["min_call_interval_seconds"] = 0
        CONFIG["usage_limits"]["max_calls_per_minute"] = 999
        CONFIG["usage_limits"]["max_calls_per_hour"] = 999

        for _ in range(8):
            tracker.record_call()

        warning = tracker.get_warning()
        assert warning is not None
        assert "8/10" in warning

    def test_no_warning_below_threshold(self, tracker):
        """Should return None when under the threshold"""
        CONFIG["usage_limits"]["max_calls_per_day"] = 10
        CONFIG["usage_limits"]["warning_threshold_pct"] = 80

        for _ in range(5):
            tracker.record_call()

        warning = tracker.get_warning()
        assert warning is None


class TestPersistence:
    def test_data_persists_across_instances(self, tmp_path):
        """Usage data should persist when a new tracker instance is created"""
        usage_file = tmp_path / "usage.json"

        CONFIG["usage_limits"]["min_call_interval_seconds"] = 0
        CONFIG["usage_limits"]["max_calls_per_minute"] = 999
        CONFIG["usage_limits"]["max_calls_per_hour"] = 999
        CONFIG["usage_limits"]["max_calls_per_day"] = 999

        # First instance: record calls
        tracker1 = UsageTracker(usage_file=str(usage_file))
        tracker1.record_call()
        tracker1.record_call()

        # Second instance: should see the calls
        tracker2 = UsageTracker(usage_file=str(usage_file))
        status = tracker2.get_status()
        assert status["calls_today"] == 2
        assert status["total_calls_all_time"] == 2


class TestDailyReset:
    def test_old_calls_cleaned_up(self, tracker):
        """Calls older than 24h should be cleaned up"""
        # Insert a call from 25 hours ago
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        tracker._data["calls"].append(old_time)
        tracker._data["total_calls"] = 1

        # Record a new call to trigger cleanup
        tracker.record_call()

        # Old call should be gone, only new one remains
        assert len(tracker._data["calls"]) == 1
        assert tracker._data["total_calls"] == 2  # total is cumulative


class TestGetStatus:
    def test_returns_correct_format(self, tracker):
        """get_status() should return a dict with expected keys"""
        status = tracker.get_status()

        assert "calls_today" in status
        assert "calls_this_hour" in status
        assert "calls_this_minute" in status
        assert "limits" in status
        assert "paused" in status
        assert "total_calls_all_time" in status

        assert status["calls_today"] == 0
        assert status["calls_this_hour"] == 0
        assert status["calls_this_minute"] == 0
