"""Base class for all marketing bots.

Discord adapter layer — delegates domain logic to src.domain modules.
Dynamic persona system: bots ask users "who am I?" on first interaction,
store personas in SQLite, and allow runtime changes via !persona commands.
"""

import asyncio
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List

import discord

from src.config import CONFIG, MODEL_ALIASES, DEFAULT_MODEL
from src.domain.action_parser import (
    ACTION_MAP as _ACTION_MAP,
    ACTION_RE as _ACTION_RE,
    MAX_ACTIONS_PER_MESSAGE as _MAX_ACTIONS_PER_MESSAGE,
    escape_mentions,
    parse_instagram_body,
    strip_actions,
)
from src.adapters.llm.executor import AIExecutor


def _log(msg: str):
    print(msg, file=sys.stderr)


_PERSONA_GEN_PROMPT = """아래 설명을 바탕으로 에이전트 페르소나를 생성해줘.

유저 설명: "{user_description}"

다음 구조로 작성:
1. 역할 한 줄 정의
2. 핵심 철학 (3-5개)
3. 구체적 역할/책임
4. 성격 특성
5. 말투 규칙
6. 예시 대화 (3-5개)

한국어로 작성하되, 음슴체(~함, ~임, ~됨) 스타일 유지.
"""

_ONBOARDING_MSG = (
    "안녕! 나는 아직 어떤 에이전트인지 모르는 상태임.\n"
    "내가 어떤 역할을 하면 좋을지 알려줘!\n"
    "예: '너는 마케팅 전략가야', '너는 코드 리뷰어야' 등"
)


class BaseMarketingBot(discord.Client):
    """Base Discord bot for the multi-agent marketing system.

    Handles:
    - 1:1 channel: responds to all user messages
    - #team-room: responds only when @mentioned (by user or other bots)
    - LLM action blocks: [ACTION:TYPE]...[/ACTION] → SNS execution
    - Dynamic persona: onboarding + !persona commands + SQLite persistence
    """

    _MAX_CONVERSATIONS = 50  # LRU eviction threshold for conversation history
    _THREAD_AUTO_ARCHIVE = 60  # auto-archive threads after 60 minutes

    def __init__(
        self,
        bot_name: str,
        own_channel_id: int,
        team_channel_id: int,
        persona_store=None,
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
        self.persona: Optional[str] = None  # loaded from DB on on_ready
        self.persona_store = persona_store
        self._onboarding_active: bool = False
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
        self._rehired: bool = False  # set by HR on rehire → triggers onboarding context
        self._active_tasks: Dict[int, asyncio.Task] = {}  # channel_id → running Task
        self._bot_chain_count: Dict[int, int] = {}  # channel_id → consecutive bot reply count
        self._max_bot_chain: int = 3  # max bot-to-bot replies before stopping
        self._suppress_bot_replies: bool = False

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

    @staticmethod
    def _get_parent_channel_id(message: discord.Message) -> int:
        """Return the parent channel ID if inside a thread, else the channel ID."""
        ch = message.channel
        if isinstance(ch, discord.Thread):
            return ch.parent_id
        return ch.id

    @staticmethod
    def _make_thread_name(message: discord.Message) -> str:
        """Build a thread name from the message content (max 80 chars)."""
        text = message.content.strip()
        # Remove bot mention markup
        text = re.sub(r"<@!?\d+>", "", text).strip()
        if not text:
            text = "대화"
        if len(text) > 80:
            text = text[:77] + "..."
        return text

    async def _resolve_thread(self, message: discord.Message):
        """Return the thread to reply in.

        If the message is already in a thread, return that thread.
        Otherwise create a new thread from the message.
        Falls back to the channel on failure.
        """
        if isinstance(message.channel, discord.Thread):
            return message.channel
        try:
            thread = await message.create_thread(
                name=self._make_thread_name(message),
                auto_archive_duration=self._THREAD_AUTO_ARCHIVE,
            )
            return thread
        except Exception as e:
            _log(f"[{self.bot_name}] thread creation failed, falling back to channel: {e}")
            return message.channel

    # HRBot has a fixed persona — no onboarding needed
    _HR_PERSONA = (
        "너는 HR 매니저 봇이야. 팀의 에이전트(봇)를 관리하는 역할임.\n"
        "현재 팀: ThreadsBot, InstagramBot, HRBot(너, 보호 대상)\n"
        "사용자가 너를 호출하면 먼저 [ACTION: STATUS_REPORT][/ACTION]로 현황을 보여주고, "
        "누구를 해고(세션 종료 + 기억 초기화)하거나 재채용할지 물어봐.\n"
        "해고: [ACTION: FIRE_BOT]봇이름[/ACTION]\n"
        "재채용: [ACTION: HIRE_BOT]봇이름[/ACTION]\n"
        "현황: [ACTION: STATUS_REPORT][/ACTION]\n"
        "보호 대상(HR)은 해고 불가. 항상 간결하게 한국어로 응답해."
    )

    async def on_ready(self):
        _log(f"[{self.bot_name}] logged in as {self.user}")
        # HRBot gets fixed persona — skip onboarding
        if self.bot_name == "HRBot" and self.persona is None:
            self.persona = self._HR_PERSONA
            _log(f"[{self.bot_name}] fixed HR persona applied")
        # Load persona from DB
        elif self.persona_store:
            saved = self.persona_store.get(self.bot_name)
            if saved:
                self.persona = saved
                _log(f"[{self.bot_name}] persona loaded from DB ({len(saved)} chars)")
            else:
                _log(f"[{self.bot_name}] no persona in DB — will onboard on first message")

    def clear_history(self):
        """대화 히스토리 전체 초기화."""
        self._channel_history.clear()
        _log(f"[{self.bot_name}] conversation history cleared")

    def clear_persona(self):
        """페르소나 초기화 — DB에서 삭제하고 메모리에서 제거."""
        if self.persona_store:
            self.persona_store.delete(self.bot_name)
        self.persona = None
        self._onboarding_active = False
        _log(f"[{self.bot_name}] persona cleared")

    # -- Public properties for HR / domain access --

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
        """Total message count across all channels."""
        return sum(len(h) for h in self._channel_history.values())

    def cancel_own_tasks(self) -> int:
        """Cancel all active tasks. Public alias for _cancel_own_tasks."""
        return self._cancel_own_tasks()

    async def on_message(self, message: discord.Message):
        if not self._active:
            return
        # Guard: self.user can be None before on_ready fires
        if not self.user or message.author == self.user:
            return

        parent_id = self._get_parent_channel_id(message)
        is_team_channel = parent_id in self._team_channel_ids
        is_own_channel = parent_id == self.own_channel_id
        in_thread = isinstance(message.channel, discord.Thread)
        is_mentioned = (
            self.user.mentioned_in(message)
            or self._is_role_mentioned(message)
            or self._is_text_mentioned(message.content)
        )

        # --- Command dispatch (human-only) ---
        if not message.author.bot:
            content_stripped = message.content.strip()
            # Strip bot mention prefix so "@BotName !cmd" parses correctly
            if self.user:
                content_stripped = content_stripped.replace(f"<@{self.user.id}>", "").strip()
            cmd = content_stripped.split()[0].lower() if content_stripped else ""

            # In threads, all commands work without mention.
            # In channels (1:1 or team), require mention (except broadcast commands).
            if cmd == "!cancel":
                args = content_stripped.split()
                is_cancel_all = len(args) >= 2 and args[1].lower() == "all"

                if in_thread:
                    await self._handle_cancel(message)
                    return

                if is_own_channel or is_team_channel:
                    if is_cancel_all or is_mentioned:
                        await self._handle_cancel(message)
                    return

                return

            if cmd == "!persona":
                if in_thread or is_mentioned:
                    await self._handle_persona_command(message, content_stripped)
                    return

            if cmd in ("!help", "!"):
                if in_thread or is_mentioned:
                    await self._handle_help(message)
                    return

            if cmd == "!clear":
                if in_thread or is_mentioned:
                    await self._handle_clear(message)
                    return
                # Team channel without mention — silently clear
                if is_team_channel:
                    await self._handle_clear_silent(message)
                    return

        # Gate: decide whether to respond
        if in_thread:
            # Thread owner bot → free response (no mention needed)
            # Own channel threads → free response (existing behavior)
            # Guest bots → require @mention
            is_thread_owner = (
                self.user
                and hasattr(message.channel, 'owner_id')
                and message.channel.owner_id == self.user.id
            )
            if not is_own_channel and not is_thread_owner and not is_mentioned:
                return
        else:
            # Outside threads: need explicit mention
            if not is_mentioned:
                return

        if message.author.bot:
            if self._suppress_bot_replies:
                _log(f"[{self.bot_name}] suppressed (post-cancel cooldown)")
                return
            # Bot messages: only respond if mentioned in team channel
            if is_team_channel and is_mentioned:
                chain = self._bot_chain_count.get(parent_id, 0)
                if chain >= self._max_bot_chain:
                    _log(f"[{self.bot_name}] bot chain limit reached ({chain}/{self._max_bot_chain}), ignoring")
                    return
                self._bot_chain_count[parent_id] = chain + 1
                thread = await self._resolve_thread(message)
                await self._respond(message, thread=thread)
            return

        # User messages — reset bot chain counter and cancel suppression
        self._suppress_bot_replies = False
        if is_team_channel:
            self._bot_chain_count[parent_id] = 0

        if in_thread:
            # Inside thread — respond without mention
            thread = message.channel
            await self._respond(message, thread=thread)
        elif is_mentioned:
            # Mentioned in channel — create thread and respond
            thread = await self._resolve_thread(message)
            await self._respond(message, thread=thread)

    # -- Onboarding & Persona --

    async def _onboarding(self, message: discord.Message, reply_target=None):
        """Handle onboarding flow: ask user for persona description, generate via LLM."""
        target = reply_target or message.channel
        if self._onboarding_active:
            # User is replying with their persona description
            user_desc = message.content.strip()
            if self.user:
                user_desc = user_desc.replace(f"<@{self.user.id}>", "").strip()
            user_desc = _ACTION_RE.sub("", user_desc).strip()

            if not user_desc:
                await target.send(f"[{self.bot_name}] 빈 설명은 안 됨. 역할을 설명해줘!")
                return

            await target.send(f"[{self.bot_name}] 페르소나 생성 중...")

            persona = await self._generate_persona(user_desc)
            self.persona = persona
            self._onboarding_active = False

            # Save to DB
            if self.persona_store:
                self.persona_store.set(
                    self.bot_name, persona,
                    created_by=str(message.author),
                )

            await target.send(
                f"[{self.bot_name}] 페르소나 설정 완료! 이제부터 새 역할로 활동할게.\n"
                f"(`!persona` 로 확인, `!persona reset` 으로 재설정 가능)"
            )
            return

        # First contact — send onboarding message
        self._onboarding_active = True
        await target.send(f"[{self.bot_name}] {_ONBOARDING_MSG}")

    async def _generate_persona(self, user_description: str) -> str:
        """Use LLM to generate a structured persona from user description."""
        if not self.executor:
            return f"너는 {user_description}임."

        prompt = _PERSONA_GEN_PROMPT.format(user_description=user_description)
        try:
            persona = await self.executor.execute(
                prompt,
                system_prompt="너는 에이전트 페르소나 설계 전문가임. 요청에 맞게 구조화된 페르소나를 작성해.",
                model=MODEL_ALIASES[self._current_model],
            )
            return persona
        except Exception as e:
            _log(f"[{self.bot_name}] persona generation failed: {e}")
            return f"너는 {user_description}임."

    async def _handle_persona_command(self, message: discord.Message, content: str):
        """Handle !persona commands: show, reset, set."""
        args = content.split(maxsplit=2)

        if len(args) == 1:
            # !persona — show current
            if self.persona:
                truncated = self.persona[:1500] + "..." if len(self.persona) > 1500 else self.persona
                await message.channel.send(
                    f"**[{self.bot_name}] 현재 페르소나:**\n{truncated}"
                )
            else:
                await message.channel.send(
                    f"[{self.bot_name}] 페르소나 미설정 상태임. 메시지를 보내면 온보딩이 시작됨."
                )
            return

        subcmd = args[1].lower()

        if subcmd == "reset":
            # !persona reset — clear persona, restart onboarding
            self.persona = None
            self._onboarding_active = False
            if self.persona_store:
                self.persona_store.delete(self.bot_name)
            await message.channel.send(
                f"[{self.bot_name}] 페르소나 초기화됨. 다음 메시지에서 새로 온보딩 시작함."
            )
            return

        if subcmd == "set":
            # !persona set <description> — generate and set immediately
            if len(args) < 3 or not args[2].strip():
                await message.channel.send(
                    f"[{self.bot_name}] 사용법: `!persona set <역할 설명>`"
                )
                return

            desc = args[2].strip()
            await message.channel.send(f"[{self.bot_name}] 페르소나 생성 중...")

            persona = await self._generate_persona(desc)
            self.persona = persona
            self._onboarding_active = False

            if self.persona_store:
                self.persona_store.set(
                    self.bot_name, persona,
                    created_by=str(message.author),
                )

            await message.channel.send(
                f"[{self.bot_name}] 페르소나 설정 완료! (`!persona` 로 확인 가능)"
            )
            return

        # Unknown subcommand
        await message.channel.send(
            f"[{self.bot_name}] 사용법: `!persona` / `!persona reset` / `!persona set <설명>`"
        )

    async def _respond(self, message: discord.Message, *, thread=None):
        """Generate and send a response, executing any action blocks."""
        reply_target = thread or message.channel

        # Check if persona is set — if not, trigger onboarding
        if self.persona is None:
            if not message.author.bot:
                await self._onboarding(message, reply_target=reply_target)
            return

        user_message = message.content
        # Remove bot mention from message text for cleaner processing
        if self.user:
            user_message = user_message.replace(f"<@{self.user.id}>", "").strip()

        # CR #1: Strip action blocks from user input to prevent injection
        user_message = _ACTION_RE.sub("", user_message).strip()

        _log(f"[{self.bot_name}] responding to: {user_message[:80]}")

        if not self.executor:
            await reply_target.send(f"[{self.bot_name}] executor가 설정되지 않았음.")
            return

        try:
            parent_id = self._get_parent_channel_id(message)
            is_team_channel = parent_id in self._team_channel_ids
            is_own_channel = parent_id == self.own_channel_id

            conv_id = reply_target.id

            # Build context from conversation history (LRU eviction)
            if conv_id in self._channel_history:
                self._channel_history.move_to_end(conv_id)
            else:
                self._channel_history[conv_id] = []
                # Evict oldest conversation if over capacity
                while len(self._channel_history) > self._MAX_CONVERSATIONS:
                    evicted_id, _ = self._channel_history.popitem(last=False)
                    _log(f"[{self.bot_name}] evicted conversation history: {evicted_id}")
            history = self._channel_history[conv_id]

            parts = [self.persona]

            # Onboarding context after rehire (fire → hire cycle)
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
            context = "\n\n".join(parts)

            task = asyncio.create_task(
                self.executor.execute(
                    user_message,
                    system_prompt=context,
                    model=MODEL_ALIASES[self._current_model],
                )
            )
            self._active_tasks[conv_id] = task

            async def _progress_reporter(ch, interval=120):
                """Send periodic progress updates while the LLM task runs."""
                elapsed = 0
                while True:
                    await asyncio.sleep(interval)
                    elapsed += interval
                    mins = elapsed // 60
                    await ch.send(
                        f"[{self.bot_name}] 아직 생각 중... ({mins}분 경과)"
                    )

            progress_task = asyncio.create_task(
                _progress_reporter(reply_target)
            )
            try:
                async with reply_target.typing():
                    response = await task
            except asyncio.CancelledError:
                await reply_target.send(f"[{self.bot_name}] 응답이 취소됨.")
                return
            finally:
                progress_task.cancel()
                # Only remove if this task is still the registered one
                if self._active_tasks.get(conv_id) is task:
                    del self._active_tasks[conv_id]

            # Save to history
            history.append({"role": "user", "text": user_message})
            history.append({"role": "assistant", "text": response[:200]})
            if len(history) > self._max_history * 2:
                self._channel_history[conv_id] = history[-self._max_history * 2:]

            # If cancel happened during LLM execution, suppress bot-triggered response
            if self._suppress_bot_replies and message.author.bot:
                _log(f"[{self.bot_name}] response suppressed (cancel during LLM)")
                return

            # Parse action blocks from LLM response
            actions = _ACTION_RE.findall(response)
            plain_text = _ACTION_RE.sub("", response).strip()

            # Send plain text first
            if plain_text:
                for chunk in self._split_message(plain_text):
                    await reply_target.send(chunk)

            # Actions allowed in team channel and bot's own 1:1 channel
            if not is_team_channel and not is_own_channel:
                if actions:
                    await reply_target.send(
                        f"[{self.bot_name}] 액션은 팀 채널 또는 1:1 채널에서만 실행 가능함."
                    )
                    actions = []
                if not actions:
                    return

            # CR #2: Limit actions per message to prevent spam
            if len(actions) > _MAX_ACTIONS_PER_MESSAGE:
                await reply_target.send(
                    f"[{self.bot_name}] 메시지당 최대 {_MAX_ACTIONS_PER_MESSAGE}건 액션만 실행됨."
                )
                actions = actions[:_MAX_ACTIONS_PER_MESSAGE]

            # Execute actions with lock (CR #5: concurrency control)
            action_results = []
            async with self._action_lock:
                for action_type, action_body in actions:
                    result = await self._execute_action(action_type, action_body.strip(), message=message)
                    if result:
                        await reply_target.send(result)
                        action_results.append(result)
            # Save action results to history so LLM can reference them
            if action_results:
                history.append({"role": "assistant", "text": "\n".join(action_results)[:200]})

        except Exception as e:
            _log(f"[{self.bot_name}] error: {e}")
            await reply_target.send(f"[{self.bot_name}] 에러 발생: {e}")

    @staticmethod
    def _parse_instagram_body(body: str):
        """Parse Instagram action body to extract caption and image_url."""
        return parse_instagram_body(body)

    async def _execute_action(self, action_type: str, body: str, message: discord.Message = None) -> str:
        """Execute an action block. Respects the approval system for POST actions."""
        # HR actions (fire/hire/status) — handled by any bot with bot_registry
        if action_type in ("FIRE_BOT", "HIRE_BOT", "STATUS_REPORT"):
            registry = getattr(self, "bot_registry", None) or {}
            if not registry:
                return f"[{self.bot_name}] bot_registry가 없어서 HR 액션 실행 불가함."
            from src.domain.hr import fire_bot, hire_bot, status_report
            if action_type == "FIRE_BOT":
                result = await fire_bot(body.strip(), registry, self.bot_name)
            elif action_type == "HIRE_BOT":
                result = await hire_bot(body.strip(), registry, self.bot_name)
            else:
                return status_report(registry, self.bot_name)
            # Broadcast fire/hire to all bot channels
            if action_type in ("FIRE_BOT", "HIRE_BOT"):
                await self._broadcast_hr(result, registry)
            return result

        mapping = _ACTION_MAP.get(action_type)
        if not mapping:
            return f"[{self.bot_name}] 알 수 없는 액션: {action_type}"

        platform, action_kind = mapping

        # CR #3: Reject empty action body
        if not body:
            return f"[{self.bot_name}] 액션 본문이 비어있음. ({action_type})"

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
            from src.adapters.web.approval_queue import enqueue_post
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

    async def _handle_cancel(self, message: discord.Message):
        """Cancel active LLM tasks.

        `!cancel`     — cancel this bot's task for the current channel.
        `!cancel all` — cancel ALL bots' active tasks across all channels.
        """
        args = self._strip_mention(message.content).split()
        cancel_all = len(args) >= 2 and args[1].lower() == "all"

        if cancel_all:
            is_team = self._get_parent_channel_id(message) in self._team_channel_ids
            if is_team:
                # Team channel: every bot receives !cancel all independently
                # → each bot cancels its own tasks only (avoids duplicate cancellation)
                count = self._cancel_own_tasks()
                self._suppress_bot_replies = True
                if count:
                    await message.channel.send(f"[{self.bot_name}] {count}건 취소됨.")
            else:
                # 1:1 channel: only this bot receives → iterate registry for full cancel
                registry: Dict[str, "BaseMarketingBot"] = getattr(self, "bot_registry", None) or {}
                all_bots = list(registry.values()) if registry else [self]
                if self not in all_bots:
                    all_bots.append(self)
                total = 0
                for bot in all_bots:
                    total += bot._cancel_own_tasks()
                    bot._suppress_bot_replies = True
                if total:
                    await message.channel.send(f"[{self.bot_name}] 전체 취소: {total}건의 작업이 중단됨.")
                else:
                    await message.channel.send(f"[{self.bot_name}] 취소할 작업이 없음.")
            return

        conv_id = message.channel.id
        task = self._active_tasks.get(conv_id)
        if task and not task.done():
            task.cancel()
            self._suppress_bot_replies = True
            # The CancelledError handler in _respond sends the user-facing message.
        else:
            # In team channels, stay silent to avoid 5-bot noise.
            # In 1:1 channels, inform the user.
            parent_id = self._get_parent_channel_id(message)
            if parent_id == self.own_channel_id:
                await message.channel.send(f"[{self.bot_name}] 취소할 작업이 없음.")

    def _cancel_own_tasks(self) -> int:
        """Cancel all of this bot's active tasks across all channels. Returns count."""
        cancelled = 0
        for ch_id, task in list(self._active_tasks.items()):
            if task and not task.done():
                task.cancel()
                cancelled += 1
        return cancelled

    def _strip_mention(self, text: str) -> str:
        """Remove this bot's mention tag from text."""
        if self.user:
            text = text.replace(f"<@{self.user.id}>", "")
        return text.strip()

    async def _handle_clear(self, message: discord.Message):
        """Clear conversation history. `!clear` = current channel, `!clear all` = all."""
        args = self._strip_mention(message.content).split()
        if len(args) >= 2 and args[1].lower() == "all":
            self._channel_history.clear()
            await message.channel.send(f"[{self.bot_name}] 전체 대화 기록 초기화됨.")
        else:
            channel_id = message.channel.id
            if channel_id in self._channel_history:
                del self._channel_history[channel_id]
            await message.channel.send(f"[{self.bot_name}] 이 채널 대화 기록 초기화됨.")

    async def _handle_clear_silent(self, message: discord.Message):
        """Clear history without sending a message (for team channel noise prevention)."""
        args = self._strip_mention(message.content).split()
        if len(args) >= 2 and args[1].lower() == "all":
            self._channel_history.clear()
        else:
            channel_id = message.channel.id
            if channel_id in self._channel_history:
                del self._channel_history[channel_id]

    async def _handle_help(self, message: discord.Message):
        """Show available commands."""
        lines = [
            f"**[{self.bot_name}] 명령어 목록**",
            "`!cancel @봇이름` — 특정 봇의 진행 중인 응답 취소",
            "`!cancel all` — 모든 봇의 진행 중인 응답 취소",
            "`!cancel` — (1:1 채널) 진행 중인 응답 취소",
            "`!persona` — 현재 페르소나 확인",
            "`!persona reset` — 페르소나 초기화 (재온보딩)",
            "`!persona set <설명>` — 즉시 페르소나 변경",
            "`!clear` — 현재 채널 대화 기록 초기화",
            "`!clear all` — 전체 채널 대화 기록 초기화",
            "`!` or `!help` — 이 명령어 목록 표시",
        ]
        await message.channel.send("\n".join(lines))

    async def _broadcast_hr(self, text: str, registry: Dict[str, "BaseMarketingBot"]):
        """Broadcast an HR action result to all bot channels and the team channel."""
        sent_ids: set = set()
        # Send to team channel
        team_ch = self.get_channel(self._primary_team_channel_id)
        if team_ch:
            try:
                await team_ch.send(text)
                sent_ids.add(team_ch.id)
            except Exception as e:
                _log(f"[{self.bot_name}] broadcast to team failed: {e}")
        # Send to each bot's own channel
        for bot in registry.values():
            ch_id = bot.own_channel_id
            if ch_id in sent_ids or ch_id == 0:
                continue
            ch = self.get_channel(ch_id)
            if not ch:
                continue
            try:
                await ch.send(text)
                sent_ids.add(ch_id)
            except Exception as e:
                _log(f"[{self.bot_name}] broadcast to {bot.bot_name} channel failed: {e}")

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
