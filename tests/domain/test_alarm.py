"""Tests for alarm domain logic with mock storage.

These tests verify AlarmScheduler behavior without filesystem dependency
(using temp dirs for isolation).
"""

import tempfile
from datetime import datetime, timezone

import pytest

from src.domain.alarm import AlarmScheduler


class TestAlarmSchedulerDomain:
    """Domain-level alarm tests — verifying pure scheduling logic."""

    @pytest.fixture
    def scheduler(self):
        tmp = tempfile.mkdtemp()
        return AlarmScheduler(bot_name="test", storage_dir=tmp)

    def test_add_and_list(self, scheduler):
        entry = scheduler.add_alarm(
            schedule_str="daily 09:00",
            prompt="morning briefing",
            channel_id=100,
            created_by="user",
        )
        alarms = scheduler.list_alarms()
        assert len(alarms) == 1
        assert alarms[0].alarm_id == entry.alarm_id
        assert alarms[0].prompt == "morning briefing"

    def test_remove(self, scheduler):
        entry = scheduler.add_alarm(
            schedule_str="daily 09:00",
            prompt="test",
            channel_id=100,
            created_by="user",
        )
        assert scheduler.remove_alarm(entry.alarm_id) is True
        assert scheduler.list_alarms() == []

    def test_remove_nonexistent(self, scheduler):
        assert scheduler.remove_alarm("nonexistent") is False

    def test_due_daily(self, scheduler):
        entry = scheduler.add_alarm(
            schedule_str="daily 09:00",
            prompt="test",
            channel_id=100,
            created_by="user",
            tz="UTC",
        )
        # Set time to 09:01 UTC
        now = datetime(2025, 1, 15, 9, 1, tzinfo=timezone.utc)
        due = scheduler.get_due_alarms(now)
        assert len(due) == 1

    def test_not_due_daily(self, scheduler):
        scheduler.add_alarm(
            schedule_str="daily 09:00",
            prompt="test",
            channel_id=100,
            created_by="user",
            tz="UTC",
        )
        # Set time to 08:59 UTC (before alarm)
        now = datetime(2025, 1, 15, 8, 59, tzinfo=timezone.utc)
        due = scheduler.get_due_alarms(now)
        assert len(due) == 0

    def test_mark_run_prevents_duplicate(self, scheduler):
        entry = scheduler.add_alarm(
            schedule_str="daily 09:00",
            prompt="test",
            channel_id=100,
            created_by="user",
            tz="UTC",
        )
        now = datetime(2025, 1, 15, 9, 1, tzinfo=timezone.utc)
        assert len(scheduler.get_due_alarms(now)) == 1
        scheduler.mark_run(entry.alarm_id, now)
        assert len(scheduler.get_due_alarms(now)) == 0

    def test_max_alarms_limit(self, scheduler):
        for i in range(20):
            scheduler.add_alarm(
                schedule_str="daily 09:00",
                prompt=f"alarm {i}",
                channel_id=100,
                created_by="user",
            )
        with pytest.raises(ValueError, match="제한 초과"):
            scheduler.add_alarm(
                schedule_str="daily 10:00",
                prompt="one too many",
                channel_id=100,
                created_by="user",
            )

    def test_invalid_timezone(self, scheduler):
        with pytest.raises(ValueError, match="타임존"):
            scheduler.add_alarm(
                schedule_str="daily 09:00",
                prompt="test",
                channel_id=100,
                created_by="user",
                tz="Invalid/Timezone",
            )

    def test_once_alarm(self, scheduler):
        entry = scheduler.add_alarm(
            schedule_str="once 30m",
            prompt="reminder",
            channel_id=100,
            created_by="user",
        )
        assert entry.schedule_type == "once"
        assert entry.interval_minutes == 30
        assert entry.fire_at  # should have absolute fire time
