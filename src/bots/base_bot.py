"""Base class for all marketing bots."""

import sys
from typing import Optional, Dict, List

import discord

from src.config import MODEL_ALIASES, DEFAULT_MODEL
from src.executor import AIExecutor


def _log(msg: str):
    print(msg, file=sys.stderr)


class BaseMarketingBot(discord.Client):
    """Base Discord bot for the multi-agent marketing system.

    Handles:
    - 1:1 channel: responds to all user messages
    - #team-room: responds only when @mentioned (by user or other bots)
    """

    def __init__(
        self,
        bot_name: str,
        persona: str,
        own_channel_id: int,
        team_channel_id: int,
        executor: Optional[AIExecutor] = None,
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.bot_name = bot_name
        self.persona = persona
        self.own_channel_id = own_channel_id
        self.team_channel_id = team_channel_id
        self.executor = executor
        self._channel_history: Dict[int, List[Dict[str, str]]] = {}
        self._max_history = 10
        self._current_model: str = DEFAULT_MODEL

    async def on_ready(self):
        _log(f"[{self.bot_name}] logged in as {self.user}")

    async def on_message(self, message: discord.Message):
        # Guard: self.user can be None before on_ready fires
        if not self.user or message.author == self.user:
            return

        is_team_channel = message.channel.id == self.team_channel_id
        is_own_channel = message.channel.id == self.own_channel_id
        is_mentioned = self.user.mentioned_in(message)

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
        """Generate and send a response."""
        user_message = message.content
        # Remove bot mention from message text for cleaner processing
        if self.user:
            user_message = user_message.replace(f"<@{self.user.id}>", "").strip()

        _log(f"[{self.bot_name}] responding to: {user_message[:80]}")

        if not self.executor:
            await message.channel.send(f"[{self.bot_name}] executor가 설정되지 않았음.")
            return

        try:
            channel_id = message.channel.id

            # Build context from conversation history
            if channel_id not in self._channel_history:
                self._channel_history[channel_id] = []
            history = self._channel_history[channel_id]

            parts = [self.persona]

            if history:
                lines = [f"{h['role']}: {h['text']}" for h in history[-self._max_history:]]
                parts.append("Previous conversation:\n" + "\n".join(lines))
            parts.append("Continue naturally.")
            context = "\n\n".join(parts)

            async with message.channel.typing():
                response = await self.executor.execute(
                    user_message,
                    system_prompt=context,
                    model=MODEL_ALIASES[self._current_model],
                )

            # Save to history
            history.append({"role": "user", "text": user_message})
            history.append({"role": "assistant", "text": response[:200]})
            if len(history) > self._max_history * 2:
                self._channel_history[channel_id] = history[-self._max_history * 2:]

            # Split long messages (Discord 2000 char limit)
            for chunk in self._split_message(response):
                await message.channel.send(chunk)

        except Exception as e:
            _log(f"[{self.bot_name}] error: {e}")
            await message.channel.send(f"[{self.bot_name}] 에러 발생: {e}")

    async def send_to_team(self, text: str):
        """Send a message to the team channel."""
        channel = self.get_channel(self.team_channel_id)
        if not channel:
            _log(f"[{self.bot_name}] team channel {self.team_channel_id} not accessible")
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
