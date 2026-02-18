"""Discord adapter — bridges discord.Client to AgentBrain.

This module provides DiscordBotAdapter, a thin discord.Client subclass
that converts Discord messages to IncomingMessage and delegates to AgentBrain.

For backward compatibility, BaseMarketingBot in src/bots/base_bot.py remains
the primary class used by existing code. This adapter demonstrates how the
full hexagonal split will work.
"""

import sys

import discord

from src.domain.agent import AgentBrain
from src.ports.inbound import IncomingMessage


def _log(msg: str):
    print(msg, file=sys.stderr)


class DiscordNotificationAdapter:
    """NotificationPort implementation using discord.Client."""

    def __init__(self, client: discord.Client):
        self._client = client

    async def send(self, channel_id: int, text: str) -> None:
        channel = self._client.get_channel(channel_id)
        if channel:
            # Split long messages
            while text:
                await channel.send(text[:2000])
                text = text[2000:]

    async def send_typing(self, channel_id: int) -> None:
        channel = self._client.get_channel(channel_id)
        if channel:
            await channel.typing()


class DiscordBotAdapter(discord.Client):
    """Thin Discord adapter that delegates to AgentBrain.

    Converts discord.Message -> IncomingMessage for platform-agnostic processing.
    """

    def __init__(self, brain: AgentBrain, token: str, **discord_kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, **discord_kwargs)
        self._brain = brain
        self._token = token

    def _to_incoming(self, message: discord.Message) -> IncomingMessage:
        """Convert a Discord message to platform-agnostic IncomingMessage."""
        is_mention = (
            (self.user and self.user.mentioned_in(message))
            or self._is_role_mentioned(message)
            or self._is_text_mentioned(message.content)
        )
        return IncomingMessage(
            content=message.content,
            channel_id=message.channel.id,
            author_name=str(message.author),
            author_id=message.author.id,
            is_bot=message.author.bot,
            is_mention=is_mention,
            is_team_channel=message.channel.id in self._brain._team_channel_ids,
            is_own_channel=message.channel.id == self._brain.own_channel_id,
        )

    def _is_role_mentioned(self, message: discord.Message) -> bool:
        if not message.role_mentions or not self.user:
            return False
        bot_names = {self._brain.bot_name.lower()} | {a.lower() for a in self._brain._aliases}
        return any(role.name.lower() in bot_names for role in message.role_mentions)

    def _is_text_mentioned(self, content: str) -> bool:
        if not self.user:
            return False
        names = {self._brain.bot_name, self.user.name}
        if self.user.display_name:
            names.add(self.user.display_name)
        names.update(self._brain._aliases)
        content_lower = content.lower()
        return any(f"@{name.lower()}" in content_lower for name in names)

    async def on_ready(self):
        _log(f"[{self._brain.bot_name}] logged in as {self.user}")
        # Wire up adapter callbacks via public method
        notification = DiscordNotificationAdapter(self)
        self._brain.wire(notification, self.get_channel, self.is_closed)
        await self._brain.start_alarm_loop()

    async def on_message(self, message: discord.Message):
        """Convert Discord message and delegate to AgentBrain."""
        # Ignore own messages
        if not self.user or message.author == self.user:
            return

        incoming = self._to_incoming(message)

        if not self._brain.should_respond(incoming):
            # Reset chain counter on human messages even if not responding
            if not incoming.is_bot:
                self._brain.reset_chain(incoming.channel_id)
            return

        # Chain control for bot-to-bot messages
        if incoming.is_bot:
            self._brain.increment_chain(incoming.channel_id)
            if self._brain.get_chain_count(incoming.channel_id) > self._brain._max_bot_chain:
                _log(f"[{self._brain.bot_name}] chain limit reached in ch={incoming.channel_id}")
                self._brain._suppress_bot_replies = True
                return
        else:
            self._brain.reset_chain(incoming.channel_id)

        # Check for commands
        cmd = self._brain.is_command(incoming.content)
        if cmd:
            await self._handle_command(cmd, incoming)
            return

        # Normal message — run LLM and respond
        await self._respond(incoming)

    async def _handle_command(self, cmd: str, msg: IncomingMessage):
        """Dispatch command to AgentBrain."""
        notification = self._brain._notification
        if not notification:
            return

        if cmd == "!cancel":
            count = self._brain.cancel_own_tasks()
            self._brain._suppress_bot_replies = True
            if msg.is_own_channel:
                await notification.send(msg.channel_id, f"[{self._brain.bot_name}] {count}개 작업 취소됨.")

        elif cmd == "!clear":
            self._brain.clear_history()
            if msg.is_own_channel:
                await notification.send(msg.channel_id, f"[{self._brain.bot_name}] 대화 기록 초기화됨.")

        elif cmd == "!alarms":
            alarms = self._brain._alarm_scheduler.list_alarms()
            if not alarms:
                await notification.send(msg.channel_id, f"[{self._brain.bot_name}] 등록된 알람 없음.")
            else:
                from src.domain.action_parser import escape_mentions, format_schedule
                lines = [f"[{self._brain.bot_name}] 알람 목록 ({len(alarms)}개):"]
                for a in alarms:
                    sched = format_schedule(a)
                    lines.append(f"- `{a.alarm_id}` | {sched} | {escape_mentions(a.prompt[:100])}")
                await notification.send(msg.channel_id, "\n".join(lines))

        elif cmd == "!help":
            help_text = (
                f"**[{self._brain.bot_name}] 명령어 목록**\n"
                "`!cancel` — 진행 중인 응답 취소\n"
                "`!clear` — 대화 기록 초기화\n"
                "`!alarms` — 등록된 알람 목록\n"
                "`!help` — 이 도움말"
            )
            await notification.send(msg.channel_id, help_text)

    async def _respond(self, msg: IncomingMessage):
        """Run LLM and send response."""
        if not self._brain.executor or not self._brain._notification:
            return

        from src.config import MODEL_ALIASES
        from src.domain.action_parser import parse_actions, strip_actions, escape_mentions

        await self._brain._notification.send_typing(msg.channel_id)

        context = self._brain.build_context(msg.channel_id, msg.content)
        try:
            response = await self._brain.executor.execute(
                msg.content,
                system_prompt=context,
                model=MODEL_ALIASES[self._brain._current_model],
            )
        except Exception as e:
            _log(f"[{self._brain.bot_name}] LLM error: {e}")
            return

        # Parse and execute action blocks
        actions = parse_actions(response)
        clean = strip_actions(response)
        if clean:
            safe = escape_mentions(clean)
            for chunk in self._brain._split_message(safe):
                await self._brain._notification.send(msg.channel_id, chunk)

        for action in actions:
            result = await self._brain.execute_action(
                action.action_type, action.body,
                channel_id=msg.channel_id, author=msg.author_name,
            )
            if result:
                await self._brain._notification.send(msg.channel_id, result)

        self._brain.save_to_history(msg.channel_id, msg.content, response[:200])
