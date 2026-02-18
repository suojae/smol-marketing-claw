"""Tests for multi-provider executor behavior."""

import asyncio
from pathlib import Path

import pytest

from src.adapters.llm.executor import CodexExecutor, create_executor


def run(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.run(coro)


class _FakeProc:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


def test_create_executor_rejects_unknown_provider():
    with pytest.raises(ValueError):
        create_executor("unknown-provider")


def test_codex_executor_uses_codex_exec_and_reads_output(monkeypatch):
    captured = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        output_path = args[args.index("--output-last-message") + 1]
        Path(output_path).write_text("codex-result", encoding="utf-8")
        return _FakeProc(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    executor = CodexExecutor()
    monkeypatch.setattr(executor.usage_tracker, "check_limits", lambda: None)
    monkeypatch.setattr(executor.usage_tracker, "record_call", lambda: None)

    response = run(
        executor.execute(
            "hello",
            system_prompt="system-guidance",
            session_id="session-ignored",
            model="gpt-5",
        )
    )

    args = captured["args"]
    assert args[0:2] == ("codex", "exec")
    assert "--model" in args
    assert "gpt-5" in args
    assert "System instructions:" in args[-1]
    assert "User message:" in args[-1]
    assert response == "codex-result"
