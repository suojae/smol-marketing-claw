"""Threads adapter — re-exports ThreadsClient as SNSPort implementation."""

from src.threads_client import ThreadsClient, ThreadsPostResult

__all__ = ["ThreadsClient", "ThreadsPostResult"]
