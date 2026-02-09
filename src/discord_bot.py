"""Discord bot for bidirectional communication."""

import asyncio
import os
from typing import Optional, Dict, List

import discord

from src.executor import ClaudeExecutor
from src.usage import UsageLimitExceeded
from src.config import CONFIG, MODEL_ALIASES, DEFAULT_MODEL


class DiscordBot(discord.Client):
    """Discord bot for bidirectional communication with users"""

    def __init__(self, claude: ClaudeExecutor):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.claude = claude
        self.notification_channel: Optional[discord.TextChannel] = None
        self.channel_id = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
        self._channel_history: Dict[int, List[Dict[str, str]]] = {}  # channel_id -> conversation
        self._max_history = 10
        self._current_model: str = DEFAULT_MODEL

    async def on_ready(self):
        print(f"Discord bot logged in: {self.user}")
        if self.channel_id:
            self.notification_channel = self.get_channel(self.channel_id)
            if self.notification_channel:
                print(f"Notification channel: #{self.notification_channel.name}")
            else:
                print(f"Channel ID {self.channel_id} not found")

    async def on_message(self, message: discord.Message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Only respond in the configured channel
        if self.channel_id and message.channel.id != self.channel_id:
            return

        user_message = message.content
        print(f"Discord message received: {user_message}")

        # Handle !model command
        content = message.content.strip()
        if content.startswith("!model"):
            await self._handle_model_command(message, content)
            return

        # Guardrail: block dangerous commands
        blocked_patterns = [
            "rm -rf", "sudo", "DROP TABLE", "DELETE FROM",
            "format", "mkfs", "> /dev/", "chmod 777",
            "curl | sh", "wget | sh", "eval(", "exec(",
        ]
        msg_lower = user_message.lower()
        for pattern in blocked_patterns:
            if pattern.lower() in msg_lower:
                await message.channel.send(
                    f"Security guardrail: `{pattern}` pattern detected and blocked."
                )
                print(f"Guardrail blocked: {pattern}")
                return

        try:
            channel_id = message.channel.id

            # Build context from conversation history
            if channel_id not in self._channel_history:
                self._channel_history[channel_id] = []
            history = self._channel_history[channel_id]

            context = None
            if history:
                lines = [f"{h['role']}: {h['text']}" for h in history[-self._max_history:]]
                context = "Previous conversation:\n" + "\n".join(lines) + "\n\nContinue naturally."

            async with message.channel.typing():
                try:
                    response = await self.claude.execute(
                        user_message, system_prompt=context,
                        model=MODEL_ALIASES[self._current_model],
                    )
                except UsageLimitExceeded:
                    await asyncio.sleep(CONFIG["usage_limits"]["min_call_interval_seconds"])
                    response = await self.claude.execute(
                        user_message, system_prompt=context,
                        model=MODEL_ALIASES[self._current_model],
                    )

            # Save to history
            history.append({"role": "user", "text": user_message})
            history.append({"role": "assistant", "text": response[:200]})
            # Trim history
            if len(history) > self._max_history * 2:
                self._channel_history[channel_id] = history[-self._max_history * 2:]

            # Split long messages (Discord 2000 char limit)
            for chunk in self._split_message(response):
                await message.channel.send(chunk)
        except Exception as e:
            await message.channel.send(f"Error: {e}")

    async def _handle_model_command(self, message: discord.Message, content: str):
        """Handle !model command for switching Claude models."""
        parts = content.split()
        if len(parts) == 1:
            model_id = MODEL_ALIASES[self._current_model]
            available = ", ".join(MODEL_ALIASES.keys())
            await message.channel.send(
                f"Current model: **{self._current_model}** (`{model_id}`)\n"
                f"Available: {available}"
            )
            return

        alias = parts[1].lower()
        if alias not in MODEL_ALIASES:
            available = ", ".join(MODEL_ALIASES.keys())
            await message.channel.send(
                f"Unknown model `{alias}`. Available: {available}"
            )
            return

        self._current_model = alias
        model_id = MODEL_ALIASES[alias]
        await message.channel.send(f"Model switched to **{alias}** (`{model_id}`)")

    async def send_notification(self, message: str):
        """Send a notification message to the configured channel"""
        if not self.notification_channel:
            print("Discord notification channel not configured")
            return

        try:
            for chunk in self._split_message(message):
                await self.notification_channel.send(chunk)
            print("Discord notification sent")
        except Exception as e:
            print(f"Discord notification failed: {e}")

    @staticmethod
    def _split_message(text: str, limit: int = 2000) -> List[str]:
        """Split a message into chunks that fit Discord's character limit"""
        if len(text) <= limit:
            return [text]
        chunks = []
        while text:
            chunks.append(text[:limit])
            text = text[limit:]
        return chunks
