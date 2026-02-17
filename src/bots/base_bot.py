"""Base class for all marketing bots."""

import asyncio
import re
import sys
from collections import OrderedDict
from typing import Any, Optional, Dict, List

import discord

from src.config import CONFIG, MODEL_ALIASES, DEFAULT_MODEL
from src.executor import AIExecutor


def _log(msg: str):
    print(msg, file=sys.stderr)


# Action block regex: [ACTION:TYPE] ... [/ACTION]
_ACTION_RE = re.compile(
    r"\[ACTION:(\w+)\]\s*(.*?)\s*\[/ACTION\]",
    re.DOTALL,
)

# Map ACTION codes → (platform, action_kind)
_ACTION_MAP: Dict[str, tuple] = {
    "POST_THREADS": ("threads", "post"),
    "POST_LINKEDIN": ("linkedin", "post"),
    "POST_INSTAGRAM": ("instagram", "post"),
    "POST_X": ("x", "post"),
    "SEARCH_NEWS": ("news", "search"),
}

# Max actions per single LLM response (spam prevention)
_MAX_ACTIONS_PER_MESSAGE = 2


class BaseMarketingBot(discord.Client):
    """Base Discord bot for the multi-agent marketing system.

    Handles:
    - 1:1 channel: responds to all user messages
    - #team-room: responds only when @mentioned (by user or other bots)
    - LLM action blocks: [ACTION:TYPE]...[/ACTION] → SNS execution
    """

    _MAX_CHANNELS = 20  # LRU eviction threshold for channel history

    def __init__(
        self,
        bot_name: str,
        persona: str,
        own_channel_id: int,
        team_channel_id: int,
        executor: Optional[AIExecutor] = None,
        clients: Optional[Dict[str, Any]] = None,
        extra_team_channels: Optional[List[int]] = None,
        aliases: Optional[List[str]] = None,
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.bot_name = bot_name
        self._aliases: List[str] = aliases or []
        self.persona = persona
        self.own_channel_id = own_channel_id
        self._primary_team_channel_id = team_channel_id
        self._team_channel_ids = {team_channel_id}
        if extra_team_channels:
            self._team_channel_ids.update(ch for ch in extra_team_channels if ch)
        self.executor = executor
        self._clients: Dict[str, Any] = clients or {}
        self._action_lock = asyncio.Lock()
        self._channel_history: OrderedDict[int, List[Dict[str, str]]] = OrderedDict()
        self._max_history = 10
        self._current_model: str = DEFAULT_MODEL
        self._active: bool = True
        self._active_tasks: Dict[int, asyncio.Task] = {}  # channel_id → running Task

    def _is_role_mentioned(self, message: discord.Message) -> bool:
        """Check if the bot's role is mentioned (Discord converts @BotName to role mention)."""
        if not message.role_mentions or not self.user:
            return False
        # Bot's own roles in guilds it belongs to
        for role in message.role_mentions:
            if role.name.lower() in {self.bot_name.lower()} | {a.lower() for a in self._aliases}:
                return True
        return False

    def _is_text_mentioned(self, content: str) -> bool:
        """Check if bot is mentioned by @name in plain text (LLM-generated mentions)."""
        if not self.user:
            return False
        names = {self.bot_name, self.user.name}
        if self.user.display_name:
            names.add(self.user.display_name)
        names.update(self._aliases)
        content_lower = content.lower()
        return any(f"@{name.lower()}" in content_lower for name in names)

    async def on_ready(self):
        _log(f"[{self.bot_name}] logged in as {self.user}")

    def clear_history(self):
        """대화 히스토리 전체 초기화."""
        self._channel_history.clear()
        _log(f"[{self.bot_name}] conversation history cleared")

    async def on_message(self, message: discord.Message):
        if not self._active:
            return
        # Guard: self.user can be None before on_ready fires
        if not self.user or message.author == self.user:
            return

        is_team_channel = message.channel.id in self._team_channel_ids
        is_own_channel = message.channel.id == self.own_channel_id
        is_mentioned = (
            self.user.mentioned_in(message)
            or self._is_role_mentioned(message)
            or self._is_text_mentioned(message.content)
        )

        # --- Command dispatch (human-only) ---
        if not message.author.bot:
            content_stripped = message.content.strip()
            cmd = content_stripped.split()[0].lower() if content_stripped else ""

            if cmd == "!cancel":
                # !cancel works everywhere without mention
                await self._handle_cancel(message)
                return

            if cmd in ("!clear", "!help"):
                # 1:1 channel — always handle; team channel — only when mentioned
                if is_own_channel or (is_team_channel and is_mentioned):
                    if cmd == "!clear":
                        await self._handle_clear(message)
                    else:
                        await self._handle_help(message)
                    return

        if message.author.bot:
            # Bot messages: only respond if mentioned in team channel
            if is_team_channel and is_mentioned:
                await self._respond(message)
            return

        # User messages
        if is_own_channel:
            # 1:1 channel — always respond
            await self._respond(message)
        elif is_team_channel and is_mentioned:
            # Team room — only when mentioned
            await self._respond(message)

    async def _respond(self, message: discord.Message):
        """Generate and send a response, executing any action blocks."""
        user_message = message.content
        # Remove bot mention from message text for cleaner processing
        if self.user:
            user_message = user_message.replace(f"<@{self.user.id}>", "").strip()

        # CR #1: Strip action blocks from user input to prevent injection
        user_message = _ACTION_RE.sub("", user_message).strip()

        _log(f"[{self.bot_name}] responding to: {user_message[:80]}")

        if not self.executor:
            await message.channel.send(f"[{self.bot_name}] executor가 설정되지 않았음.")
            return

        try:
            channel_id = message.channel.id
            is_team_channel = channel_id in self._team_channel_ids

            # Build context from conversation history (LRU eviction)
            if channel_id in self._channel_history:
                self._channel_history.move_to_end(channel_id)
            else:
                self._channel_history[channel_id] = []
                # Evict oldest channel if over capacity
                while len(self._channel_history) > self._MAX_CHANNELS:
                    evicted_id, _ = self._channel_history.popitem(last=False)
                    _log(f"[{self.bot_name}] evicted channel history: {evicted_id}")
            history = self._channel_history[channel_id]

            parts = [self.persona]

            if history:
                lines = [f"{h['role']}: {h['text']}" for h in history[-self._max_history:]]
                parts.append("Previous conversation:\n" + "\n".join(lines))
            parts.append("Continue naturally.")
            context = "\n\n".join(parts)

            channel_id_for_task = message.channel.id
            task = asyncio.create_task(
                self.executor.execute(
                    user_message,
                    system_prompt=context,
                    model=MODEL_ALIASES[self._current_model],
                )
            )
            self._active_tasks[channel_id_for_task] = task
            try:
                async with message.channel.typing():
                    response = await task
            except asyncio.CancelledError:
                await message.channel.send(f"[{self.bot_name}] 응답이 취소됨.")
                return
            finally:
                # Only remove if this task is still the registered one
                if self._active_tasks.get(channel_id_for_task) is task:
                    del self._active_tasks[channel_id_for_task]

            # Save to history
            history.append({"role": "user", "text": user_message})
            history.append({"role": "assistant", "text": response[:200]})
            if len(history) > self._max_history * 2:
                self._channel_history[channel_id] = history[-self._max_history * 2:]

            # Parse action blocks from LLM response
            actions = _ACTION_RE.findall(response)
            plain_text = _ACTION_RE.sub("", response).strip()

            # Send plain text first
            if plain_text:
                for chunk in self._split_message(plain_text):
                    await message.channel.send(chunk)

            # CR #1: Only execute actions in team channel (not 1:1 user channels)
            if not is_team_channel:
                if actions:
                    await message.channel.send(
                        f"[{self.bot_name}] 액션은 팀 채널에서만 실행 가능함."
                    )
                return

            # CR #2: Limit actions per message to prevent spam
            if len(actions) > _MAX_ACTIONS_PER_MESSAGE:
                await message.channel.send(
                    f"[{self.bot_name}] 메시지당 최대 {_MAX_ACTIONS_PER_MESSAGE}건 액션만 실행됨."
                )
                actions = actions[:_MAX_ACTIONS_PER_MESSAGE]

            # Execute actions with lock (CR #5: concurrency control)
            async with self._action_lock:
                for action_type, action_body in actions:
                    result = await self._execute_action(action_type, action_body.strip())
                    if result:
                        await message.channel.send(result)

        except Exception as e:
            _log(f"[{self.bot_name}] error: {e}")
            await message.channel.send(f"[{self.bot_name}] 에러 발생: {e}")

    @staticmethod
    def _parse_instagram_body(body: str):
        """Parse Instagram action body to extract caption and image_url."""
        lines = body.strip().splitlines()
        image_url = ""
        caption_lines = []
        for line in lines:
            if line.strip().lower().startswith("image_url:"):
                image_url = line.split(":", 1)[1].strip()
            else:
                caption_lines.append(line)
        return "\n".join(caption_lines).strip(), image_url

    async def _execute_action(self, action_type: str, body: str) -> str:
        """Execute an action block. Respects the approval system for POST actions."""
        mapping = _ACTION_MAP.get(action_type)
        if not mapping:
            return f"[{self.bot_name}] 알 수 없는 액션: {action_type}"

        # CR #3: Reject empty action body
        if not body:
            return f"[{self.bot_name}] 액션 본문이 비어있음. ({action_type})"

        platform, action_kind = mapping

        # SEARCH_NEWS — execute immediately, no approval needed
        if action_type == "SEARCH_NEWS":
            return await self._execute_search(body)

        # POST actions — check approval setting
        client = self._clients.get(platform)
        if not client:
            return f"[{self.bot_name}] {platform} 클라이언트가 연결되지 않았음."

        # Instagram needs image_url parsed from body
        meta = {}
        post_text = body
        if platform == "instagram":
            post_text, image_url = self._parse_instagram_body(body)
            # CR #3: Reject empty caption
            if not post_text:
                return f"[{self.bot_name}] Instagram 캡션이 비어있음."
            # CR #4: Validate image_url scheme (SSRF prevention)
            if image_url and not image_url.startswith("https://"):
                return f"[{self.bot_name}] Instagram image_url은 https:// 만 허용됨."
            if image_url:
                meta["image_url"] = image_url

        if CONFIG["require_manual_approval"]:
            from src.approval import enqueue_post
            result = await enqueue_post(platform, action_kind, post_text, meta=meta)
            return f"[{self.bot_name}] 승인 대기 중 (ID: {result['approval_id']})"

        # CR #2: Audit log for direct execution (approval disabled)
        _log(f"[{self.bot_name}] AUDIT: direct post to {platform} — "
             f"{post_text[:100]!r}")
        try:
            if platform == "instagram":
                res = await client.post(post_text, meta.get("image_url", ""))
            else:
                res = await client.post(post_text)
            if res.success:
                _log(f"[{self.bot_name}] AUDIT: posted to {platform} — "
                     f"post_id={res.post_id}")
                return f"[{self.bot_name}] {platform} 포스팅 완료 (ID: {res.post_id})"
            _log(f"[{self.bot_name}] AUDIT: post failed on {platform} — "
                 f"{res.error}")
            return f"[{self.bot_name}] {platform} 포스팅 실패: {res.error}"
        except Exception as e:
            _log(f"[{self.bot_name}] AUDIT: post error on {platform} — {e}")
            return f"[{self.bot_name}] {platform} 포스팅 에러: {e}"

    async def _execute_search(self, query: str) -> str:
        """Execute a news search immediately."""
        client = self._clients.get("news")
        if not client:
            return f"[{self.bot_name}] news 클라이언트가 연결되지 않았음."
        try:
            result = await client.search(query)
            if not result.success:
                return f"[{self.bot_name}] 뉴스 검색 실패: {result.error}"
            if not result.items:
                return f"[{self.bot_name}] '{query}' 검색 결과 없음."
            lines = [f"[{self.bot_name}] '{query}' 검색 결과:"]
            for item in result.items[:5]:
                lines.append(f"- {item.text[:200]}")
                if item.url:
                    lines.append(f"  {item.url}")
            return "\n".join(lines)
        except Exception as e:
            return f"[{self.bot_name}] 뉴스 검색 에러: {e}"

    async def _handle_cancel(self, message: discord.Message):
        """Cancel the active LLM task for this channel, if any."""
        channel_id = message.channel.id
        task = self._active_tasks.get(channel_id)
        if task and not task.done():
            task.cancel()
            # The CancelledError handler in _respond sends the user-facing message.
        else:
            # In team channels, stay silent to avoid 5-bot noise.
            # In 1:1 channels, inform the user.
            if channel_id == self.own_channel_id:
                await message.channel.send(f"[{self.bot_name}] 취소할 작업이 없음.")

    async def _handle_clear(self, message: discord.Message):
        """Clear conversation history. `!clear` = current channel, `!clear all` = all."""
        args = message.content.strip().split()
        if len(args) >= 2 and args[1].lower() == "all":
            self._channel_history.clear()
            await message.channel.send(f"[{self.bot_name}] 전체 대화 기록 초기화됨.")
        else:
            channel_id = message.channel.id
            if channel_id in self._channel_history:
                del self._channel_history[channel_id]
            await message.channel.send(f"[{self.bot_name}] 이 채널 대화 기록 초기화됨.")

    async def _handle_help(self, message: discord.Message):
        """Show available commands."""
        lines = [
            f"**[{self.bot_name}] 명령어 목록**",
            "`!cancel` — 진행 중인 응답 취소",
            "`!clear` — 현재 채널 대화 기록 초기화",
            "`!clear all` — 전체 채널 대화 기록 초기화",
            "`!help` — 이 명령어 목록 표시",
        ]
        await message.channel.send("\n".join(lines))

    async def send_to_team(self, text: str):
        """Send a message to the first (primary) team channel."""
        channel = self.get_channel(self._primary_team_channel_id)
        if not channel:
            _log(f"[{self.bot_name}] team channel {self._primary_team_channel_id} not accessible")
            return
        try:
            for chunk in self._split_message(text):
                await channel.send(chunk)
        except Exception as e:
            _log(f"[{self.bot_name}] send_to_team failed: {e}")

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
