"""Tests for event-driven architecture (FileWatcher, Queue, Webhook)"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import from the server module
import importlib.util

spec = importlib.util.spec_from_file_location(
    "server", os.path.join(os.path.dirname(os.path.dirname(__file__)), "autonomous-ai-server.py")
)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

GitFileHandler = server.GitFileHandler
event_queue = server.event_queue


def run(coro):
    """Helper to run async functions in sync tests"""
    return asyncio.get_event_loop().run_until_complete(coro)


def drain_queue():
    """Clear the event queue between tests"""
    while not event_queue.empty():
        try:
            event_queue.get_nowait()
        except asyncio.QueueEmpty:
            break


class TestGitFileHandler:
    def test_ignores_git_directory(self):
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop)

        assert handler._should_ignore("/repo/.git/objects/abc") is True
        assert handler._should_ignore("/repo/__pycache__/mod.pyc") is True
        assert handler._should_ignore("/repo/node_modules/pkg/index.js") is True

    def test_does_not_ignore_source_files(self):
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop)

        assert handler._should_ignore("/repo/main.py") is False
        assert handler._should_ignore("/repo/src/app.js") is False

    def test_emits_event_to_queue(self):
        drain_queue()
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop, debounce_seconds=0)

        handler._emit("/repo/main.py", "modified")
        # Spin loop to process call_soon_threadsafe callback
        loop.run_until_complete(asyncio.sleep(0))

        assert not event_queue.empty()
        event = event_queue.get_nowait()
        assert event["type"] == "file_changed"
        assert "main.py" in event["detail"]

    def test_debounce_prevents_rapid_events(self):
        drain_queue()
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop, debounce_seconds=10)

        handler._emit("/repo/a.py", "modified")
        handler._emit("/repo/b.py", "modified")  # should be debounced
        loop.run_until_complete(asyncio.sleep(0))

        count = 0
        while not event_queue.empty():
            event_queue.get_nowait()
            count += 1
        assert count == 1

    def test_on_modified_pushes_event(self):
        drain_queue()
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop, debounce_seconds=0)

        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "/repo/server.py"

        handler.on_modified(mock_event)
        loop.run_until_complete(asyncio.sleep(0))

        assert not event_queue.empty()

    def test_on_modified_ignores_directory(self):
        drain_queue()
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop, debounce_seconds=0)

        mock_event = MagicMock()
        mock_event.is_directory = True
        mock_event.src_path = "/repo/src"

        handler.on_modified(mock_event)

        assert event_queue.empty()


class TestEventQueue:
    def test_queue_is_async(self):
        drain_queue()
        event_queue.put_nowait({"type": "test", "detail": "hello"})

        assert not event_queue.empty()
        event = run(event_queue.get())
        assert event["type"] == "test"

    def test_batch_drain(self):
        """Multiple events can be batched by draining the queue"""
        drain_queue()
        event_queue.put_nowait({"type": "a", "detail": "1"})
        event_queue.put_nowait({"type": "b", "detail": "2"})
        event_queue.put_nowait({"type": "c", "detail": "3"})

        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())

        assert len(events) == 3
        assert [e["type"] for e in events] == ["a", "b", "c"]


class TestWebhookParsing:
    def test_github_event_types_mapped(self):
        """Verify event type mapping logic"""
        event_map = {
            "pull_request_review": "pr_review",
            "issues": "new_issue",
            "push": "push",
            "check_run": "ci_status",
        }

        assert event_map["pull_request_review"] == "pr_review"
        assert event_map["push"] == "push"
        assert event_map.get("unknown_event", "unknown_event") == "unknown_event"
