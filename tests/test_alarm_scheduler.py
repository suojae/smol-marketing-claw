"""Tests for AlarmScheduler — parsing, CRUD, due-checking, persistence."""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from src.domain.alarm import AlarmScheduler, _MIN_INTERVAL_MINUTES, _MAX_ALARMS_PER_BOT


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for alarm storage."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def scheduler(tmp_dir):
    return AlarmScheduler(bot_name="TestBot", storage_dir=tmp_dir)


# ---------------------------------------------------------------------------
# Schedule parsing
# ---------------------------------------------------------------------------

class TestParseSchedule:
    def test_daily(self, scheduler):
        result = scheduler._parse_schedule("daily 09:00")
        assert result == {"type": "daily", "hour": 9, "minute": 0}

    def test_daily_afternoon(self, scheduler):
        result = scheduler._parse_schedule("daily 14:30")
        assert result == {"type": "daily", "hour": 14, "minute": 30}

    def test_weekday(self, scheduler):
        result = scheduler._parse_schedule("weekday 09:00")
        assert result == {"type": "weekday", "hour": 9, "minute": 0}

    def test_every_hours(self, scheduler):
        result = scheduler._parse_schedule("every 2h")
        assert result == {"type": "interval", "interval_minutes": 120}

    def test_every_minutes(self, scheduler):
        result = scheduler._parse_schedule("every 30m")
        assert result == {"type": "interval", "interval_minutes": 30}

    def test_case_insensitive(self, scheduler):
        result = scheduler._parse_schedule("Daily 09:00")
        assert result["type"] == "daily"

    def test_invalid_format(self, scheduler):
        with pytest.raises(ValueError, match="잘못된 스케줄 형식"):
            scheduler._parse_schedule("weekly 09:00")

    def test_invalid_hour(self, scheduler):
        with pytest.raises(ValueError, match="잘못된 시간"):
            scheduler._parse_schedule("daily 25:00")

    def test_invalid_minute(self, scheduler):
        with pytest.raises(ValueError, match="잘못된 시간"):
            scheduler._parse_schedule("daily 09:61")

    def test_interval_too_short(self, scheduler):
        with pytest.raises(ValueError, match="최소 간격"):
            scheduler._parse_schedule("every 5m")

    def test_interval_hours_too_short(self, scheduler):
        """0h → 0 minutes, below minimum."""
        with pytest.raises(ValueError):
            scheduler._parse_schedule("every 0h")

    def test_once_hours(self, scheduler):
        result = scheduler._parse_schedule("once 1h")
        assert result == {"type": "once", "interval_minutes": 60}

    def test_once_minutes(self, scheduler):
        result = scheduler._parse_schedule("once 30m")
        assert result == {"type": "once", "interval_minutes": 30}

    def test_once_case_insensitive(self, scheduler):
        result = scheduler._parse_schedule("Once 2H")
        assert result["type"] == "once"

    def test_once_too_short(self, scheduler):
        with pytest.raises(ValueError, match="최소 간격"):
            scheduler._parse_schedule("once 5m")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestCRUD:
    def test_add_alarm(self, scheduler):
        entry = scheduler.add_alarm("daily 09:00", "뉴스 요약", 12345, "user1")
        assert entry.schedule_type == "daily"
        assert entry.hour == 9
        assert entry.minute == 0
        assert entry.prompt == "뉴스 요약"
        assert entry.channel_id == 12345
        assert entry.created_by == "user1"
        assert entry.enabled is True
        assert len(entry.alarm_id) == 8

    def test_list_alarms(self, scheduler):
        scheduler.add_alarm("daily 09:00", "p1", 1, "u1")
        scheduler.add_alarm("every 2h", "p2", 2, "u2")
        alarms = scheduler.list_alarms()
        assert len(alarms) == 2

    def test_remove_alarm(self, scheduler):
        entry = scheduler.add_alarm("daily 09:00", "p1", 1, "u1")
        assert scheduler.remove_alarm(entry.alarm_id) is True
        assert scheduler.list_alarms() == []

    def test_remove_nonexistent(self, scheduler):
        assert scheduler.remove_alarm("nonexist") is False

    def test_max_alarms_limit(self, scheduler):
        for i in range(_MAX_ALARMS_PER_BOT):
            scheduler.add_alarm("daily 09:00", f"p{i}", i, "u")
        with pytest.raises(ValueError, match="알람 개수 제한"):
            scheduler.add_alarm("daily 10:00", "extra", 999, "u")

    def test_invalid_timezone(self, scheduler):
        with pytest.raises(ValueError, match="잘못된 타임존"):
            scheduler.add_alarm("daily 09:00", "p", 1, "u", tz="Invalid/Zone")


# ---------------------------------------------------------------------------
# Due-checking
# ---------------------------------------------------------------------------

class TestGetDueAlarms:
    def test_daily_due(self, scheduler):
        entry = scheduler.add_alarm("daily 09:00", "test", 1, "u", tz="Asia/Seoul")
        # Simulate: 9:01 AM in Seoul
        from zoneinfo import ZoneInfo
        seoul = ZoneInfo("Asia/Seoul")
        now_seoul = datetime.now(seoul).replace(hour=9, minute=1, second=0)
        now_utc = now_seoul.astimezone(timezone.utc)

        due = scheduler.get_due_alarms(now_utc)
        assert len(due) == 1
        assert due[0].alarm_id == entry.alarm_id

    def test_daily_not_yet(self, scheduler):
        scheduler.add_alarm("daily 09:00", "test", 1, "u", tz="Asia/Seoul")
        from zoneinfo import ZoneInfo
        seoul = ZoneInfo("Asia/Seoul")
        now_seoul = datetime.now(seoul).replace(hour=8, minute=59, second=0)
        now_utc = now_seoul.astimezone(timezone.utc)

        due = scheduler.get_due_alarms(now_utc)
        assert len(due) == 0

    def test_daily_already_ran_today(self, scheduler):
        entry = scheduler.add_alarm("daily 09:00", "test", 1, "u", tz="Asia/Seoul")
        from zoneinfo import ZoneInfo
        seoul = ZoneInfo("Asia/Seoul")
        now_seoul = datetime.now(seoul).replace(hour=10, minute=0, second=0)
        now_utc = now_seoul.astimezone(timezone.utc)

        # Mark as run today
        scheduler.mark_run(entry.alarm_id, now_utc - timedelta(hours=1))

        due = scheduler.get_due_alarms(now_utc)
        assert len(due) == 0

    def test_weekday_skips_weekend(self, scheduler):
        scheduler.add_alarm("weekday 09:00", "test", 1, "u", tz="UTC")
        # Find the next Saturday
        now = datetime.now(timezone.utc)
        days_until_saturday = (5 - now.weekday()) % 7
        if days_until_saturday == 0 and now.weekday() != 5:
            days_until_saturday = 7
        saturday = (now + timedelta(days=days_until_saturday)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        # Make sure it's actually Saturday
        if saturday.weekday() != 5:
            saturday = saturday + timedelta(days=(5 - saturday.weekday()) % 7)

        due = scheduler.get_due_alarms(saturday)
        assert len(due) == 0

    def test_interval_first_run(self, scheduler):
        """First run of interval alarm should fire immediately."""
        entry = scheduler.add_alarm("every 30m", "test", 1, "u", tz="UTC")
        now = datetime.now(timezone.utc)
        due = scheduler.get_due_alarms(now)
        assert len(due) == 1

    def test_interval_not_yet_elapsed(self, scheduler):
        entry = scheduler.add_alarm("every 2h", "test", 1, "u", tz="UTC")
        now = datetime.now(timezone.utc)
        scheduler.mark_run(entry.alarm_id, now)

        # 30 minutes later → not due
        due = scheduler.get_due_alarms(now + timedelta(minutes=30))
        assert len(due) == 0

    def test_interval_elapsed(self, scheduler):
        entry = scheduler.add_alarm("every 2h", "test", 1, "u", tz="UTC")
        now = datetime.now(timezone.utc)
        scheduler.mark_run(entry.alarm_id, now)

        # 2 hours and 1 minute later → due
        due = scheduler.get_due_alarms(now + timedelta(hours=2, minutes=1))
        assert len(due) == 1

    def test_mark_run_prevents_duplicate(self, scheduler):
        """After mark_run, daily alarm should not fire again on same day."""
        entry = scheduler.add_alarm("daily 09:00", "test", 1, "u", tz="UTC")
        now = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0)

        due = scheduler.get_due_alarms(now)
        assert len(due) == 1

        scheduler.mark_run(entry.alarm_id, now)

        due = scheduler.get_due_alarms(now + timedelta(minutes=1))
        assert len(due) == 0

    def test_once_not_yet_due(self, scheduler):
        """once alarm should not fire before fire_at time."""
        entry = scheduler.add_alarm("once 1h", "test", 1, "u", tz="UTC")
        # Immediately after creation, not yet due (fire_at is ~1h in the future)
        now = datetime.now(timezone.utc)
        due = scheduler.get_due_alarms(now)
        assert len(due) == 0

    def test_once_due_after_elapsed(self, scheduler):
        """once alarm should fire after fire_at time."""
        entry = scheduler.add_alarm("once 1h", "test", 1, "u", tz="UTC")
        # Simulate time 2 hours later
        now = datetime.now(timezone.utc) + timedelta(hours=2)
        due = scheduler.get_due_alarms(now)
        assert len(due) == 1
        assert due[0].alarm_id == entry.alarm_id

    def test_once_not_due_after_run(self, scheduler):
        """once alarm should not fire again after it has been run."""
        entry = scheduler.add_alarm("once 1h", "test", 1, "u", tz="UTC")
        now = datetime.now(timezone.utc) + timedelta(hours=2)
        scheduler.mark_run(entry.alarm_id, now)
        due = scheduler.get_due_alarms(now + timedelta(minutes=1))
        assert len(due) == 0

    def test_disabled_alarm_skipped(self, scheduler):
        entry = scheduler.add_alarm("daily 09:00", "test", 1, "u", tz="UTC")
        entry.enabled = False
        scheduler._save()

        now = datetime.now(timezone.utc).replace(hour=10)
        due = scheduler.get_due_alarms(now)
        assert len(due) == 0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_load_roundtrip(self, tmp_dir):
        s1 = AlarmScheduler(bot_name="PersistBot", storage_dir=tmp_dir)
        s1.add_alarm("daily 09:00", "morning news", 100, "alice", tz="Asia/Seoul")
        s1.add_alarm("every 2h", "check prices", 200, "bob", tz="UTC")

        # Create new scheduler instance that loads from same file
        s2 = AlarmScheduler(bot_name="PersistBot", storage_dir=tmp_dir)
        alarms = s2.list_alarms()
        assert len(alarms) == 2

        types = {a.schedule_type for a in alarms}
        assert types == {"daily", "interval"}

        prompts = {a.prompt for a in alarms}
        assert prompts == {"morning news", "check prices"}

    def test_load_empty_file(self, tmp_dir):
        """Scheduler should handle missing file gracefully."""
        s = AlarmScheduler(bot_name="NoFile", storage_dir=tmp_dir)
        assert s.list_alarms() == []

    def test_once_persistence_roundtrip(self, tmp_dir):
        """once alarm should preserve fire_at through save/load cycle."""
        s1 = AlarmScheduler(bot_name="OnceBot", storage_dir=tmp_dir)
        entry = s1.add_alarm("once 2h", "remind me", 100, "alice", tz="UTC")
        assert entry.fire_at != ""
        assert entry.schedule_type == "once"

        s2 = AlarmScheduler(bot_name="OnceBot", storage_dir=tmp_dir)
        alarms = s2.list_alarms()
        assert len(alarms) == 1
        assert alarms[0].fire_at == entry.fire_at
        assert alarms[0].schedule_type == "once"
        assert alarms[0].interval_minutes == 120

    def test_load_corrupted_file(self, tmp_dir):
        """Scheduler should handle corrupted JSON gracefully."""
        path = os.path.join(tmp_dir, "alarms_CorruptBot.json")
        with open(path, "w") as f:
            f.write("{invalid json")
        s = AlarmScheduler(bot_name="CorruptBot", storage_dir=tmp_dir)
        assert s.list_alarms() == []
