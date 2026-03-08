"""AgentBrain — core agent logic, no framework dependencies.

Encapsulates message routing, command handling, and action execution
without any Discord dependency.
"""

import asyncio
import sys
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from src.config import CONFIG, MODEL_ALIASES, DEFAULT_MODEL
from src.domain.action_parser import (
    ACTION_MAP,
    ACTION_RE,
    MAX_ACTIONS_PER_MESSAGE,
    escape_mentions,
    parse_instagram_body,
    strip_actions,
)
from src.ports.inbound import IncomingMessage
from src.ports.outbound import ApprovalPort, LLMPort, NotificationPort


def _log(msg: str):
    print(msg, file=sys.stderr)


class AgentBrain:
    """Pure agent logic — no discord import, testable with mock ports.

    Handles:
    - Message routing (should I respond?)
    - Command dispatch (!cancel, !clear, !help)
    - LLM invocation via LLMPort
    - Action block execution
    - Bot chain limiting
    """

    _MAX_CHANNELS = 20

    def __init__(
        self,
        bot_name: str,
        persona: str,
        executor: Optional[LLMPort] = None,
        clients: Optional[Dict[str, Any]] = None,
        notification: Optional[NotificationPort] = None,
        approval: Optional[ApprovalPort] = None,
        aliases: Optional[List[str]] = None,
        own_channel_id: int = 0,
        team_channel_ids: Optional[set] = None,
        primary_team_channel_id: int = 0,
        storage_dir: str = "memory",
    ):
        self.bot_name = bot_name
        self._aliases: List[str] = aliases or []
        self.persona = persona
        self.own_channel_id = own_channel_id
        self._primary_team_channel_id = primary_team_channel_id
        self._team_channel_ids = team_channel_ids or set()
        self.executor = executor
        self._clients: Dict[str, Any] = clients or {}
        self._notification = notification
        self._approval = approval
        self._action_lock = asyncio.Lock()
        self._channel_history: OrderedDict[int, List[Dict[str, str]]] = OrderedDict()
        self._max_history = 10
        self._current_model: str = DEFAULT_MODEL
        self._active: bool = True
        self._rehired: bool = False
        self._active_tasks: Dict[int, asyncio.Task] = {}
        self._bot_chain_count: Dict[int, int] = {}
        self._max_bot_chain: int = 3
        self._suppress_bot_replies: bool = False

    # -- Public properties for HR / adapter access --

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool):
        self._active = value

    @property
    def rehired(self) -> bool:
        return self._rehired

    @rehired.setter
    def rehired(self, value: bool):
        self._rehired = value

    def history_message_count(self) -> int:
        """Total message count across all channels (for HR status reports)."""
        return sum(len(h) for h in self._channel_history.values())

    def clear_history(self):
        """Clear all conversation history."""
        self._channel_history.clear()
        _log(f"[{self.bot_name}] conversation history cleared")

    def should_respond(self, msg: IncomingMessage) -> bool:
        """Determine if this brain should respond to the message."""
        if not self._active:
            return False

        if msg.is_bot:
            if self._suppress_bot_replies:
                return False
            return msg.is_team_channel and msg.is_mention

        # User messages
        if msg.is_own_channel:
            return True
        if msg.is_team_channel and msg.is_mention:
            return True
        return False

    def is_command(self, content: str) -> Optional[str]:
        """Check if content is a command. Returns command name or None."""
        stripped = content.strip()
        if not stripped:
            return None
        cmd = stripped.split()[0].lower()
        if cmd in ("!cancel", "!clear", "!help"):
            return cmd
        return None

    def get_chain_count(self, channel_id: int) -> int:
        """Get current bot chain count for a channel."""
        return self._bot_chain_count.get(channel_id, 0)

    def increment_chain(self, channel_id: int):
        """Increment bot chain counter."""
        self._bot_chain_count[channel_id] = self._bot_chain_count.get(channel_id, 0) + 1

    def reset_chain(self, channel_id: int):
        """Reset bot chain counter (on human message)."""
        self._suppress_bot_replies = False
        self._bot_chain_count[channel_id] = 0

    def cancel_own_tasks(self) -> int:
        """Cancel all of this brain's active tasks across all channels."""
        cancelled = 0
        for ch_id, task in list(self._active_tasks.items()):
            if task and not task.done():
                task.cancel()
                cancelled += 1
        return cancelled

    def build_context(self, channel_id: int, user_message: str) -> str:
        """Build LLM context from persona + history."""
        if channel_id in self._channel_history:
            self._channel_history.move_to_end(channel_id)
        else:
            self._channel_history[channel_id] = []
            while len(self._channel_history) > self._MAX_CHANNELS:
                evicted_id, _ = self._channel_history.popitem(last=False)
                _log(f"[{self.bot_name}] evicted channel history: {evicted_id}")
        history = self._channel_history[channel_id]

        parts = [self.persona]

        if self._rehired:
            parts.append(
                "[시스템 알림] 너는 방금 해고(컨텍스트 초기화) 후 재채용되었음. "
                "이전 대화 기록은 전부 삭제된 상태임. "
                "새로 온보딩한다고 생각하고, 팀에 합류 인사 후 업무에 바로 복귀할 것."
            )
            self._rehired = False

        if history:
            lines = [f"{h['role']}: {h['text']}" for h in history[-self._max_history:]]
            parts.append("Previous conversation:\n" + "\n".join(lines))
        parts.append("Continue naturally.")
        return "\n\n".join(parts)

    def save_to_history(self, channel_id: int, user_message: str, response: str):
        """Save exchange to channel history."""
        history = self._channel_history.get(channel_id, [])
        history.append({"role": "user", "text": user_message})
        history.append({"role": "assistant", "text": response[:200]})
        if len(history) > self._max_history * 2:
            history = history[-self._max_history * 2:]
        self._channel_history[channel_id] = history

    async def execute_action(self, action_type: str, body: str,
                             channel_id: int = 0, author: str = "") -> str:
        """Execute an action block. Can be overridden by subclasses."""
        mapping = ACTION_MAP.get(action_type)
        if not mapping:
            return f"[{self.bot_name}] 알 수 없는 액션: {action_type}"

        platform, action_kind = mapping

        if not body:
            return f"[{self.bot_name}] 액션 본문이 비어있음. ({action_type})"

        client = self._clients.get(platform)
        if not client:
            return f"[{self.bot_name}] {platform} 클라이언트가 연결되지 않았음."

        meta = {}
        post_text = body
        if platform == "instagram":
            post_text, image_url = parse_instagram_body(body)
            if not post_text:
                return f"[{self.bot_name}] Instagram 캡션이 비어있음."
            if image_url and not image_url.startswith("https://"):
                return f"[{self.bot_name}] Instagram image_url은 https:// 만 허용됨."
            if image_url:
                meta["image_url"] = image_url

        if CONFIG["require_manual_approval"] and self._approval:
            result = await self._approval.enqueue(platform, action_kind, post_text, meta=meta)
            return f"[{self.bot_name}] 승인 대기 중 (ID: {result['approval_id']})"

        _log(f"[{self.bot_name}] AUDIT: direct post to {platform} — {post_text[:100]!r}")
        try:
            if platform == "instagram":
                res = await client.post(post_text, meta.get("image_url", ""))
            else:
                res = await client.post(post_text)
            if res.success:
                _log(f"[{self.bot_name}] AUDIT: posted to {platform} — post_id={res.post_id}")
                return f"[{self.bot_name}] {platform} 포스팅 완료 (ID: {res.post_id})"
            _log(f"[{self.bot_name}] AUDIT: post failed on {platform} — {res.error}")
            return f"[{self.bot_name}] {platform} 포스팅 실패: {res.error}"
        except Exception as e:
            _log(f"[{self.bot_name}] AUDIT: post error on {platform} — {e}")
            return f"[{self.bot_name}] {platform} 포스팅 에러: {e}"

    @staticmethod
    def _split_message(text: str, limit: int = 2000) -> List[str]:
        """Split a message into chunks that fit Discord's character limit."""
        if len(text) <= limit:
            return [text]
        chunks = []
        while text:
            chunks.append(text[:limit])
            text = text[limit:]
        return chunks
