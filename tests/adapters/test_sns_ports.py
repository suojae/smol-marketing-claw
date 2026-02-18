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
        from src.x_client import XClient
        client = XClient()
        assert hasattr(client, "is_configured")
        assert hasattr(client, "post")

    def test_threads_client_has_interface(self):
        from src.threads_client import ThreadsClient
        client = ThreadsClient()
        assert hasattr(client, "is_configured")
        assert hasattr(client, "post")

    def test_linkedin_client_has_interface(self):
        from src.linkedin_client import LinkedInClient
        client = LinkedInClient()
        assert hasattr(client, "is_configured")
        assert hasattr(client, "post")

    def test_instagram_client_has_interface(self):
        from src.instagram_client import InstagramClient
        client = InstagramClient()
        assert hasattr(client, "is_configured")
        assert hasattr(client, "post")

    def test_news_client_has_interface(self):
        from src.news_client import NewsClient
        client = NewsClient()
        assert hasattr(client, "is_configured")
        assert hasattr(client, "search")


class TestLLMPortConformance:
    """Verify that executor classes have the expected interface."""

    def test_claude_executor_has_interface(self):
        from src.executor import ClaudeExecutor
        e = ClaudeExecutor()
        assert hasattr(e, "execute")
        assert hasattr(e, "usage_tracker")

    def test_codex_executor_has_interface(self):
        from src.executor import CodexExecutor
        e = CodexExecutor()
        assert hasattr(e, "execute")
        assert hasattr(e, "usage_tracker")


class TestAdapterReexports:
    """Verify adapter modules correctly re-export original clients."""

    def test_x_adapter(self):
        from src.adapters.sns.x_adapter import XClient as AdapterXClient
        from src.x_client import XClient
        assert AdapterXClient is XClient

    def test_threads_adapter(self):
        from src.adapters.sns.threads_adapter import ThreadsClient as AdapterClient
        from src.threads_client import ThreadsClient
        assert AdapterClient is ThreadsClient

    def test_linkedin_adapter(self):
        from src.adapters.sns.linkedin_adapter import LinkedInClient as AdapterClient
        from src.linkedin_client import LinkedInClient
        assert AdapterClient is LinkedInClient

    def test_instagram_adapter(self):
        from src.adapters.sns.instagram_adapter import InstagramClient as AdapterClient
        from src.instagram_client import InstagramClient
        assert AdapterClient is InstagramClient

    def test_news_adapter(self):
        from src.adapters.sns.news_adapter import NewsClient as AdapterClient
        from src.news_client import NewsClient
        assert AdapterClient is NewsClient
