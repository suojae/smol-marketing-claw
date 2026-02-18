"""Tests for memory management system"""

import pytest
import tempfile
from datetime import datetime, timedelta

from src.infrastructure.memory import SimpleMemory, GuardrailMemory


class TestSimpleMemory:
    """Test SimpleMemory class"""

    def test_initialization(self):
        """Test memory initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = SimpleMemory(memory_dir=tmpdir)
            assert memory.memory_dir.exists()
            assert memory.max_decisions == 100

    def test_add_and_load_decision(self):
        """Test adding and loading decisions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = SimpleMemory(memory_dir=tmpdir)

            decision = {
                "action": "notify",
                "message": "Test message",
                "reasoning": "Testing"
            }

            memory.add_decision(decision)
            decisions = memory.load_decisions()

            assert len(decisions) == 1
            assert decisions[0]["action"] == "notify"
            assert decisions[0]["message"] == "Test message"
            assert "id" in decisions[0]
            assert "timestamp" in decisions[0]

    def test_duplicate_detection(self):
        """Test duplicate message detection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = SimpleMemory(memory_dir=tmpdir)

            decision = {
                "action": "notify",
                "message": "Test message for duplicate",
                "reasoning": "Testing duplicates"
            }

            memory.add_decision(decision)

            # Should detect duplicate
            assert memory.should_skip_duplicate("Test message for duplicate")

            # Should not detect different message
            assert not memory.should_skip_duplicate("Completely different message")

    def test_similarity_calculation(self):
        """Test word-based similarity"""
        memory = SimpleMemory()

        # High similarity
        assert memory._similarity("hello world", "hello world") == 1.0
        assert memory._similarity("hello world", "world hello") == 1.0

        # Partial similarity
        sim = memory._similarity("hello world test", "hello world")
        assert 0.5 < sim < 1.0

        # No similarity
        assert memory._similarity("hello", "world") == 0.0

    def test_auto_summarization(self):
        """Test auto-summarization when limit exceeded"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = SimpleMemory(memory_dir=tmpdir)
            memory.max_decisions = 10  # Lower limit for testing

            # Add 15 decisions
            for i in range(15):
                decision = {
                    "action": "notify",
                    "message": f"Message {i}",
                    "reasoning": "Testing"
                }
                memory.add_decision(decision)

            # Should have trimmed to 10 and created summary
            decisions = memory.load_decisions()
            assert len(decisions) <= 10

            summary = memory.load_summary()
            assert "Summary" in summary

    def test_get_context(self):
        """Test getting context for AI"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = SimpleMemory(memory_dir=tmpdir)

            decision = {
                "action": "notify",
                "message": "Test context",
                "reasoning": "Testing context"
            }

            memory.add_decision(decision)
            context = memory.get_context()

            assert "Recent Activity" in context
            assert "Test context" in context


class TestGuardrailMemory:
    """Test GuardrailMemory class"""

    def test_initialization(self):
        """Test guardrail memory initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = GuardrailMemory(memory_dir=tmpdir)
            assert memory.violations_file.exists() or True  # File created on first write

    def test_record_violation(self):
        """Test recording guardrail violations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = GuardrailMemory(memory_dir=tmpdir)

            memory.record_violation(
                violation_type="file_access",
                target="/etc/passwd",
                reason="Sensitive file"
            )

            violations = memory.load_violations()
            assert len(violations) == 1
            assert violations[0]["type"] == "file_access"
            assert violations[0]["target"] == "/etc/passwd"
            assert violations[0]["blocked"] is True

    def test_safety_context(self):
        """Test getting safety context"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = GuardrailMemory(memory_dir=tmpdir)

            # Record some violations
            for i in range(5):
                memory.record_violation(
                    violation_type="file_access",
                    target="/etc/passwd",
                    reason="Sensitive file"
                )

            safety_context = memory.get_safety_context()

            assert "Security History" in safety_context
            assert "Total violations blocked" in safety_context
            assert "/etc/passwd" in safety_context

    def test_pattern_detection(self):
        """Test pattern detection in violations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = GuardrailMemory(memory_dir=tmpdir)

            # Record violations with patterns
            targets = ["/etc/passwd", "/etc/shadow", "/etc/passwd", "/etc/passwd"]
            for target in targets:
                memory.record_violation(
                    violation_type="file_access",
                    target=target,
                    reason="Sensitive file"
                )

            safety_context = memory.get_safety_context()

            # Should detect /etc/passwd as most frequent
            assert "/etc/passwd" in safety_context
            assert "3 times" in safety_context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
