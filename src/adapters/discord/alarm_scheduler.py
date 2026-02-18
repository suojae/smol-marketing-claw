"""Backward-compatibility shim — AlarmScheduler now lives in src.domain.alarm."""

from src.domain.alarm import (  # noqa: F401
    AlarmEntry,
    AlarmScheduler,
    _MAX_ALARMS_PER_BOT,
    _MIN_INTERVAL_MINUTES,
)
