"""Tests for SNS Port protocol conformance.

Verifies that all SNS clients implement the expected interface.
"""

import pytest

from src.ports.outbound import PostResult, SNSPort


class TestPostResult:
    def test_success_result(self):
        r = PostResult(success=True, post_id="123", text="hello")
        assert r.success is True
        assert r.post_id == "123"

    def test_failure_result(self):
        r = PostResult(success=False, error="rate limited")
        assert r.success is False
        assert r.error == "rate limited"

    def test_defaults(self):
        r = PostResult(success=True)
        assert r.post_id is None
        assert r.text is None
        assert r.error is None


class TestSNSPortConformance:
    """Verify that SNS clients have the expected interface."""

    def test_x_client_has_interface(self):
        from src.adapters.sns.x_client import XClient
        client = XClient()
        assert hasattr(client, "is_configured")
        assert hasattr(client, "post")

    def test_threads_client_has_interface(self):
        from src.adapters.sns.threads_client import ThreadsClient
        client = ThreadsClient()
        assert hasattr(client, "is_configured")
        assert hasattr(client, "post")

    def test_linkedin_client_has_interface(self):
        from src.adapters.sns.linkedin_client import LinkedInClient
        client = LinkedInClient()
        assert hasattr(client, "is_configured")
        assert hasattr(client, "post")

    def test_instagram_client_has_interface(self):
        from src.adapters.sns.instagram_client import InstagramClient
        client = InstagramClient()
        assert hasattr(client, "is_configured")
        assert hasattr(client, "post")

    def test_news_client_has_interface(self):
        from src.adapters.sns.news_client import NewsClient
        client = NewsClient()
        assert hasattr(client, "is_configured")
        assert hasattr(client, "search")


class TestLLMPortConformance:
    """Verify that executor classes have the expected interface."""

    def test_claude_executor_has_interface(self):
        from src.adapters.llm.executor import ClaudeExecutor
        e = ClaudeExecutor()
        assert hasattr(e, "execute")
        assert hasattr(e, "usage_tracker")

    def test_codex_executor_has_interface(self):
        from src.adapters.llm.executor import CodexExecutor
        e = CodexExecutor()
        assert hasattr(e, "execute")
        assert hasattr(e, "usage_tracker")


class TestAdapterReexports:
    """Verify adapter SNS modules expose correct classes."""

    def test_x_client(self):
        from src.adapters.sns.x_client import XClient
        assert XClient is not None

    def test_threads_client(self):
        from src.adapters.sns.threads_client import ThreadsClient
        assert ThreadsClient is not None

    def test_linkedin_client(self):
        from src.adapters.sns.linkedin_client import LinkedInClient
        assert LinkedInClient is not None

    def test_instagram_client(self):
        from src.adapters.sns.instagram_client import InstagramClient
        assert InstagramClient is not None

    def test_news_client(self):
        from src.adapters.sns.news_client import NewsClient
        assert NewsClient is not None
