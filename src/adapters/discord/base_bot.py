"""Base class for all marketing bots.

Discord adapter layer — delegates domain logic to src.domain modules.
"""

import asyncio
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List

import discord

from src.domain.alarm import AlarmEntry, AlarmScheduler
from src.config import CONFIG, MODEL_ALIASES, DEFAULT_MODEL
from src.domain.action_parser import (
    ACTION_MAP as _ACTION_MAP,
    ACTION_RE as _ACTION_RE,
    MAX_ACTIONS_PER_MESSAGE as _MAX_ACTIONS_PER_MESSAGE,
    escape_mentions,
    format_schedule,
    parse_alarm_body,
    parse_instagram_body,
    strip_actions,
)
from src.adapters.llm.executor import AIExecutor


def _log(msg: str):
    print(msg, file=sys.stderr)


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
        self._rehired: bool = False  # set by HR on rehire → triggers onboarding context
        self._active_tasks: Dict[int, asyncio.Task] = {}  # channel_id → running Task
        self._bot_chain_count: Dict[int, int] = {}  # channel_id → consecutive bot reply count
        self._max_bot_chain: int = 3  # max bot-to-bot replies before stopping
        self._suppress_bot_replies: bool = False
        self._alarm_scheduler = AlarmScheduler(bot_name=bot_name)
        self._alarm_loop_task: Optional[asyncio.Task] = None
        self._alarm_fire_tasks: set = set()  # track in-flight alarm tasks for cleanup
        self._in_flight_alarms: set = set()  # alarm IDs currently executing (prevent duplicate fire)

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
        if not self._alarm_loop_task or self._alarm_loop_task.done():
            self._alarm_loop_task = asyncio.create_task(self._alarm_loop())

    def clear_history(self):
        """대화 히스토리 전체 초기화."""
        self._channel_history.clear()
        _log(f"[{self.bot_name}] conversation history cleared")

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
            # Strip bot mention prefix so "@BotName !cmd" parses correctly
            if self.user:
                content_stripped = content_stripped.replace(f"<@{self.user.id}>", "").strip()
            cmd = content_stripped.split()[0].lower() if content_stripped else ""

            if cmd == "!cancel":
                args = content_stripped.split()
                is_cancel_all = len(args) >= 2 and args[1].lower() == "all"

                if is_own_channel:
                    # 1:1 channel — always cancel own task
                    await self._handle_cancel(message)
                    return

                if is_team_channel:
                    if is_cancel_all or is_mentioned:
                        # !cancel all → all bots cancel
                        # !cancel @BotName → only mentioned bot cancels
                        await self._handle_cancel(message)
                    return

                return

            if cmd == "!alarms":
                if is_own_channel or (is_team_channel and is_mentioned):
                    await self._handle_alarms(message)
                    return

            if cmd == "!help":
                # 1:1 channel — always handle
                # Team channel — TeamLead responds as representative to avoid 6-bot noise
                if is_own_channel or (is_team_channel and (is_mentioned or self.bot_name == "TeamLead")):
                    await self._handle_help(message)
                    return

            if cmd == "!clear":
                # 1:1 channel — always handle
                if is_own_channel or (is_team_channel and (is_mentioned or self.bot_name == "TeamLead")):
                    await self._handle_clear(message)
                    return
                # Team channel without mention — silently clear (TeamLead sends confirmation)
                if is_team_channel:
                    await self._handle_clear_silent(message)
                    return

        if message.author.bot:
            if self._suppress_bot_replies:
                _log(f"[{self.bot_name}] suppressed (post-cancel cooldown)")
                return
            # Bot messages: only respond if mentioned in team channel
            if is_team_channel and is_mentioned:
                chain = self._bot_chain_count.get(message.channel.id, 0)
                if chain >= self._max_bot_chain:
                    _log(f"[{self.bot_name}] bot chain limit reached ({chain}/{self._max_bot_chain}), ignoring")
                    return
                self._bot_chain_count[message.channel.id] = chain + 1
                await self._respond(message)
            return

        # User messages — reset bot chain counter and cancel suppression
        self._suppress_bot_replies = False
        if is_team_channel:
            self._bot_chain_count[message.channel.id] = 0

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
            is_own_channel = channel_id == self.own_channel_id

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

            channel_id_for_task = message.channel.id
            task = asyncio.create_task(
                self.executor.execute(
                    user_message,
                    system_prompt=context,
                    model=MODEL_ALIASES[self._current_model],
                )
            )
            self._active_tasks[channel_id_for_task] = task

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
                _progress_reporter(message.channel)
            )
            try:
                async with message.channel.typing():
                    response = await task
            except asyncio.CancelledError:
                await message.channel.send(f"[{self.bot_name}] 응답이 취소됨.")
                return
            finally:
                progress_task.cancel()
                # Only remove if this task is still the registered one
                if self._active_tasks.get(channel_id_for_task) is task:
                    del self._active_tasks[channel_id_for_task]

            # Save to history
            history.append({"role": "user", "text": user_message})
            history.append({"role": "assistant", "text": response[:200]})
            if len(history) > self._max_history * 2:
                self._channel_history[channel_id] = history[-self._max_history * 2:]

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
                    await message.channel.send(chunk)

            # Actions allowed in team channel and bot's own 1:1 channel
            # Alarm actions (SET_ALARM, CANCEL_ALARM) are allowed everywhere
            _ALARM_ACTIONS = {"SET_ALARM", "CANCEL_ALARM"}
            if not is_team_channel and not is_own_channel:
                alarm_actions = [(t, b) for t, b in actions if t in _ALARM_ACTIONS]
                non_alarm_actions = [(t, b) for t, b in actions if t not in _ALARM_ACTIONS]
                if non_alarm_actions:
                    await message.channel.send(
                        f"[{self.bot_name}] 액션은 팀 채널 또는 1:1 채널에서만 실행 가능함."
                    )
                actions = alarm_actions
                if not actions:
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
                    result = await self._execute_action(action_type, action_body.strip(), message=message)
                    if result:
                        await message.channel.send(result)

        except Exception as e:
            _log(f"[{self.bot_name}] error: {e}")
            await message.channel.send(f"[{self.bot_name}] 에러 발생: {e}")

    @staticmethod
    def _parse_instagram_body(body: str):
        """Parse Instagram action body to extract caption and image_url."""
        return parse_instagram_body(body)

    async def _execute_action(self, action_type: str, body: str, message: discord.Message = None) -> str:
        """Execute an action block. Respects the approval system for POST actions."""
        mapping = _ACTION_MAP.get(action_type)
        if not mapping:
            return f"[{self.bot_name}] 알 수 없는 액션: {action_type}"

        platform, action_kind = mapping

        # Alarm actions (handle before empty body guard — they have their own validation)
        if action_type == "SET_ALARM":
            if not message:
                return f"[{self.bot_name}] 알람 등록 실패: 메시지 컨텍스트 없음"
            return await self._execute_set_alarm(body, message)
        if action_type == "CANCEL_ALARM":
            return await self._execute_cancel_alarm(body)

        # CR #3: Reject empty action body (after alarm actions which have own validation)
        if not body:
            return f"[{self.bot_name}] 액션 본문이 비어있음. ({action_type})"

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
        """Cancel active LLM tasks.

        `!cancel`     — cancel this bot's task for the current channel.
        `!cancel all` — cancel ALL bots' active tasks across all channels.
        """
        args = message.content.strip().split()
        cancel_all = len(args) >= 2 and args[1].lower() == "all"

        if cancel_all:
            is_team = message.channel.id in self._team_channel_ids
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

        channel_id = message.channel.id
        task = self._active_tasks.get(channel_id)
        if task and not task.done():
            task.cancel()
            self._suppress_bot_replies = True
            # The CancelledError handler in _respond sends the user-facing message.
        else:
            # In team channels, stay silent to avoid 5-bot noise.
            # In 1:1 channels, inform the user.
            if channel_id == self.own_channel_id:
                await message.channel.send(f"[{self.bot_name}] 취소할 작업이 없음.")

    def _cancel_own_tasks(self) -> int:
        """Cancel all of this bot's active tasks across all channels. Returns count."""
        cancelled = 0
        for ch_id, task in list(self._active_tasks.items()):
            if task and not task.done():
                task.cancel()
                cancelled += 1
        return cancelled

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

    async def _handle_clear_silent(self, message: discord.Message):
        """Clear history without sending a message (for team channel noise prevention)."""
        args = message.content.strip().split()
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
            "`!alarms` — 등록된 알람 목록 조회",
            "`!alarms cancel <ID>` — 특정 알람 취소",
            "`!alarms cancel all` — 전체 알람 취소",
            "`!clear` — 현재 채널 대화 기록 초기화",
            "`!clear all` — 전체 채널 대화 기록 초기화",
            "`!help` — 이 명령어 목록 표시",
        ]
        await message.channel.send("\n".join(lines))

    async def _alarm_loop(self):
        """Check alarms every 60 seconds and fire due ones."""
        _log(f"[{self.bot_name}] alarm loop started, {len(self._alarm_scheduler.list_alarms())} alarm(s) loaded")
        while not self.is_closed():
            await asyncio.sleep(60)
            try:
                now = datetime.now(timezone.utc)
                all_alarms = self._alarm_scheduler.list_alarms()
                due = self._alarm_scheduler.get_due_alarms(now)
                if all_alarms:
                    _log(f"[{self.bot_name}] alarm check: {len(all_alarms)} total, {len(due)} due (UTC={now.strftime('%H:%M')})")
                for alarm in due:
                    if alarm.alarm_id in self._in_flight_alarms:
                        continue
                    task = asyncio.create_task(self._fire_alarm(alarm))
                    self._alarm_fire_tasks.add(task)
                    task.add_done_callback(self._alarm_fire_tasks.discard)
            except Exception as e:
                _log(f"[{self.bot_name}] alarm loop error: {e}")

    async def _fire_alarm(self, alarm: AlarmEntry):
        """Execute alarm: run LLM with prompt → send result to channel."""
        _log(f"[{self.bot_name}] _fire_alarm START: {alarm.alarm_id} ch={alarm.channel_id}")
        self._in_flight_alarms.add(alarm.alarm_id)
        # Mark run BEFORE execution to prevent duplicate fire on slow LLM calls
        self._alarm_scheduler.mark_run(alarm.alarm_id, datetime.now(timezone.utc))
        try:
            channel = self.get_channel(alarm.channel_id)
            if not channel:
                _log(f"[{self.bot_name}] alarm {alarm.alarm_id}: channel {alarm.channel_id} not found")
                return
            _log(f"[{self.bot_name}] alarm {alarm.alarm_id}: channel found, calling executor...")
            if not self.executor:
                _log(f"[{self.bot_name}] alarm {alarm.alarm_id}: no executor")
                return
            # Sanitize prompt: strip any injected action blocks
            safe_prompt = _ACTION_RE.sub("", alarm.prompt).strip()
            response = await self.executor.execute(
                safe_prompt,
                system_prompt=self.persona,
                model=MODEL_ALIASES[self._current_model],
            )
            _log(f"[{self.bot_name}] alarm {alarm.alarm_id}: executor returned {len(response)} chars")
            # Security: strip action blocks from alarm-triggered responses
            response = _ACTION_RE.sub("", response).strip()
            prefix = f"[{self.bot_name}] 알람 ({alarm.alarm_id})\n"
            for chunk in self._split_message(prefix + response):
                await channel.send(chunk)
            _log(f"[{self.bot_name}] alarm {alarm.alarm_id}: sent to channel OK")
            # once 알람은 실행 후 자동 삭제
            if alarm.schedule_type == "once":
                self._alarm_scheduler.remove_alarm(alarm.alarm_id)
                _log(f"[{self.bot_name}] alarm {alarm.alarm_id}: once alarm auto-removed")
        except Exception as e:
            _log(f"[{self.bot_name}] alarm {alarm.alarm_id} failed: {e}")
        finally:
            self._in_flight_alarms.discard(alarm.alarm_id)

    async def _handle_alarms(self, message: discord.Message):
        """Handle !alarms command with subcommands: list, cancel <id>, cancel all."""
        args = message.content.strip().split()
        # !alarms cancel all
        if len(args) >= 3 and args[1].lower() == "cancel" and args[2].lower() == "all":
            alarms = self._alarm_scheduler.list_alarms()
            if not alarms:
                await message.channel.send(f"[{self.bot_name}] 취소할 알람 없음.")
                return
            count = 0
            for a in alarms:
                self._alarm_scheduler.remove_alarm(a.alarm_id)
                count += 1
            await message.channel.send(f"[{self.bot_name}] 전체 알람 {count}건 취소 완료.")
            return

        # !alarms cancel <alarm_id>
        if len(args) >= 3 and args[1].lower() == "cancel":
            alarm_id = args[2]
            if self._alarm_scheduler.remove_alarm(alarm_id):
                await message.channel.send(f"[{self.bot_name}] 알람 `{alarm_id}` 취소 완료.")
            else:
                await message.channel.send(f"[{self.bot_name}] 알람 `{alarm_id}`을(를) 찾을 수 없음.")
            return

        # !alarms (list)
        alarms = self._alarm_scheduler.list_alarms()
        if not alarms:
            await message.channel.send(f"[{self.bot_name}] 등록된 알람 없음.")
            return
        lines = [f"**[{self.bot_name}] 알람 목록 ({len(alarms)}건)**"]
        for a in alarms:
            sched = self._format_schedule(a)
            prompt_summary = a.prompt[:20] + "..." if len(a.prompt) > 20 else a.prompt
            last = a.last_run[:16] if a.last_run else "미실행"
            lines.append(f"- `{a.alarm_id}` | {sched} | {prompt_summary} | 마지막: {last}")
        await message.channel.send("\n".join(lines))

    @staticmethod
    def _escape_mentions(text: str) -> str:
        """Escape @mentions to prevent triggering other bots."""
        return escape_mentions(text)

    @staticmethod
    def _format_schedule(alarm: AlarmEntry) -> str:
        """Format alarm schedule for display."""
        return format_schedule(alarm)

    async def _execute_set_alarm(self, body: str, message: discord.Message) -> str:
        """Parse SET_ALARM body and register alarm."""
        fields = self._parse_alarm_body(body)
        schedule = fields.get("schedule", "").strip()
        prompt = fields.get("prompt", "").strip()
        tz = fields.get("timezone", "Asia/Seoul").strip()

        if not schedule:
            return f"[{self.bot_name}] 알람 등록 실패: schedule 필드 누락"
        if not prompt:
            return f"[{self.bot_name}] 알람 등록 실패: prompt 필드 누락"

        try:
            entry = self._alarm_scheduler.add_alarm(
                schedule_str=schedule,
                prompt=prompt,
                channel_id=message.channel.id,
                created_by=str(message.author),
                tz=tz,
            )
            sched_display = self._format_schedule(entry)
            return (
                f"[{self.bot_name}] 알람 등록 완료\n"
                f"- ID: `{entry.alarm_id}`\n"
                f"- 스케줄: {sched_display}\n"
                f"- 프롬프트: {self._escape_mentions(entry.prompt[:200])}"
            )
        except ValueError as e:
            return f"[{self.bot_name}] 알람 등록 실패: {e}"

    async def _execute_cancel_alarm(self, body: str) -> str:
        """Parse CANCEL_ALARM body and remove alarm."""
        fields = self._parse_alarm_body(body)
        alarm_id = fields.get("alarm_id", "").strip()
        if not alarm_id:
            # Try raw body as alarm ID
            alarm_id = body.strip()
        if not alarm_id:
            return f"[{self.bot_name}] 알람 취소 실패: alarm_id 필드 누락"
        if self._alarm_scheduler.remove_alarm(alarm_id):
            return f"[{self.bot_name}] 알람 `{alarm_id}` 취소 완료"
        return f"[{self.bot_name}] 알람 `{alarm_id}`을(를) 찾을 수 없음"

    @staticmethod
    def _parse_alarm_body(body: str) -> Dict[str, str]:
        """Parse key: value lines from action body."""
        return parse_alarm_body(body)

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
