"""Outbound ports — interfaces for external system adapters."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class PostResult:
    """Unified result type for SNS post operations."""

    success: bool
    post_id: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None


@runtime_checkable
class LLMPort(Protocol):
    """Interface for LLM execution backends."""

    async def execute(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str: ...


@runtime_checkable
class SNSPort(Protocol):
    """Interface for SNS platform clients."""

    @property
    def is_configured(self) -> bool: ...

    async def post(self, text: str, **kwargs) -> PostResult: ...


@runtime_checkable
class StoragePort(Protocol):
    """Interface for persistent storage."""

    def load(self, key: str) -> list: ...
    def save(self, key: str, data: list) -> None: ...


@runtime_checkable
class NotificationPort(Protocol):
    """Interface for sending messages to channels."""

    async def send(self, channel_id: int, text: str) -> None: ...
    async def send_typing(self, channel_id: int) -> None: ...


@runtime_checkable
class ApprovalPort(Protocol):
    """Interface for post approval queue."""

    async def enqueue(
        self,
        platform: str,
        action_kind: str,
        text: str,
        meta: Optional[Dict[str, str]] = None,
    ) -> dict: ...
