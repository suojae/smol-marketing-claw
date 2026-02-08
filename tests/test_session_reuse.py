"""Tests for AutonomousEngine session reuse"""

import pytest

from src.engine import AutonomousEngine
from src.executor import ClaudeExecutor
from src.context import ContextCollector


class TestSessionReuse:
    def _make_engine(self):
        claude = ClaudeExecutor()
        context = ContextCollector()
        engine = AutonomousEngine(claude, context)
        return engine

    def test_first_call_creates_session(self):
        engine = self._make_engine()
        assert engine._session_id is None
        assert engine._session_call_count == 0

        session_id = engine._get_or_reset_session()
        assert session_id is not None
        assert engine._session_call_count == 0

    def test_session_persists_within_limit(self):
        engine = self._make_engine()
        first_id = engine._get_or_reset_session()

        # Simulate calls within limit
        engine._session_call_count = 10
        second_id = engine._get_or_reset_session()

        assert first_id == second_id

    def test_session_resets_at_limit(self):
        engine = self._make_engine()
        first_id = engine._get_or_reset_session()

        # Simulate reaching the limit
        engine._session_call_count = engine.MAX_CALLS_PER_SESSION
        second_id = engine._get_or_reset_session()

        assert first_id != second_id
        assert engine._session_call_count == 0

    def test_is_first_call_in_session(self):
        engine = self._make_engine()
        engine._get_or_reset_session()

        assert engine.is_first_call_in_session is True

        engine._session_call_count = 1
        assert engine.is_first_call_in_session is False

    def test_max_calls_per_session_default(self):
        assert AutonomousEngine.MAX_CALLS_PER_SESSION == 50

    def test_session_resets_multiple_times(self):
        engine = self._make_engine()
        seen_ids = set()

        for _ in range(3):
            session_id = engine._get_or_reset_session()
            seen_ids.add(session_id)
            engine._session_call_count = engine.MAX_CALLS_PER_SESSION

        # Should have created 3 different sessions
        assert len(seen_ids) == 3
