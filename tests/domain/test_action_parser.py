"""Tests for domain/action_parser.py — pure Python, no Discord dependency."""

import pytest

from src.domain.action_parser import (
    ACTION_MAP,
    ACTION_RE,
    MAX_ACTIONS_PER_MESSAGE,
    escape_mentions,
    parse_actions,
    parse_instagram_body,
    strip_actions,
)
from src.domain.models import ActionBlock


class TestParseActions:
    def test_single_action(self):
        text = "Hello [ACTION:POST_X]tweet text[/ACTION] bye"
        actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0].action_type == "POST_X"
        assert actions[0].body == "tweet text"

    def test_multiple_actions(self):
        text = (
            "[ACTION:POST_X]tweet[/ACTION] "
            "[ACTION:POST_THREADS]thread post[/ACTION]"
        )
        actions = parse_actions(text)
        assert len(actions) == 2
        assert actions[0].action_type == "POST_X"
        assert actions[1].action_type == "POST_THREADS"

    def test_no_actions(self):
        text = "just plain text"
        actions = parse_actions(text)
        assert len(actions) == 0

    def test_multiline_body(self):
        text = "[ACTION:POST_THREADS]\nline1\nline2\n[/ACTION]"
        actions = parse_actions(text)
        assert len(actions) == 1
        assert "line1" in actions[0].body

    def test_action_block_dataclass(self):
        ab = ActionBlock(action_type="POST_X", body="hello")
        assert ab.action_type == "POST_X"
        assert ab.body == "hello"


class TestStripActions:
    def test_strips_all(self):
        text = "hello [ACTION:POST_X]tweet[/ACTION] world"
        result = strip_actions(text)
        assert result == "hello  world"

    def test_no_actions(self):
        text = "just text"
        assert strip_actions(text) == "just text"

    def test_empty_after_strip(self):
        text = "[ACTION:POST_X]tweet[/ACTION]"
        assert strip_actions(text) == ""


class TestEscapeMentions:
    def test_escapes_at_mentions(self):
        assert escape_mentions("@TeamLead hello") == "`@TeamLead` hello"

    def test_multiple_mentions(self):
        result = escape_mentions("@bot1 and @bot2")
        assert "`@bot1`" in result
        assert "`@bot2`" in result

    def test_no_mentions(self):
        assert escape_mentions("no mentions") == "no mentions"


class TestParseInstagramBody:
    def test_with_image_url(self):
        body = "caption text here\nimage_url: https://example.com/img.jpg"
        caption, url = parse_instagram_body(body)
        assert caption == "caption text here"
        assert url == "https://example.com/img.jpg"

    def test_without_image_url(self):
        body = "just a caption"
        caption, url = parse_instagram_body(body)
        assert caption == "just a caption"
        assert url == ""

    def test_multiline_caption(self):
        body = "line 1\nline 2\nimage_url: https://img.com/x.jpg"
        caption, url = parse_instagram_body(body)
        assert caption == "line 1\nline 2"
        assert url == "https://img.com/x.jpg"


class TestActionMap:
    def test_all_actions_mapped(self):
        expected_keys = {
            "POST_THREADS", "POST_INSTAGRAM", "POST_X",
            "FIRE_BOT", "HIRE_BOT", "STATUS_REPORT",
        }
        assert set(ACTION_MAP.keys()) == expected_keys

    def test_max_actions(self):
        assert MAX_ACTIONS_PER_MESSAGE == 2
