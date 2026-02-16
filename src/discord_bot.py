"""Discord bot for bidirectional communication."""

import asyncio
import json
import os
import uuid
import warnings
from typing import Optional, Dict, List

import discord

from src.executor import AIExecutor
from src.usage import UsageLimitExceeded
from src.config import CONFIG, MODEL_ALIASES, DEFAULT_MODEL, AI_PROVIDER
from src.persona import BOT_PERSONA

SENTIMENT_SYSTEM_PROMPT = (
    "사용자 메시지의 어조를 분석해서 AI 봇의 감정에 미칠 영향을 판단해라.\n"
    "- 칭찬, 감사, 격려 → dopamine 상승\n"
    "- 비난, 분노, 명령적 어조, 다그침 → cortisol 상승\n"
    "- 중립적 질문 → 변화 없음\n"
    'JSON만 반환: {"dopamine_delta": float, "cortisol_delta": float}\n'
    "각 값 범위: -0.2 ~ 0.2"
)


class DiscordBot(discord.Client):
    """Discord bot for bidirectional communication with users"""

    def __init__(
        self,
        executor: Optional[AIExecutor] = None,
        hormones=None,
        claude: Optional[AIExecutor] = None,  # backward compatibility
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        if executor is not None and claude is not None:
            raise ValueError("pass either executor or claude, not both")
        if executor is None and claude is not None:
            warnings.warn(
                "`claude` argument is deprecated; use `executor` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            executor = claude
        if executor is None:
            raise ValueError("executor is required")

        self.executor = executor
        self.hormones = hormones
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

        # Handle commands
        content = message.content.strip()
        if content.startswith("!model"):
            await self._handle_model_command(message, content)
            return
        if content.startswith("!hormones"):
            await self._handle_hormones_command(message)
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
                if self.hormones:
                    self.hormones.trigger_cortisol(0.3)
                return

        # Hormone decay — prevent unbounded accumulation in Discord path
        if self.hormones:
            self.hormones.decay()

        # Sentiment analysis — run before main response so the tone affects behavior
        await self._analyze_sentiment(user_message)

        try:
            channel_id = message.channel.id

            # Build context from conversation history
            if channel_id not in self._channel_history:
                self._channel_history[channel_id] = []
            history = self._channel_history[channel_id]

            parts = [BOT_PERSONA]

            # Inject hormone state into system prompt
            if self.hormones:
                params = self.hormones.get_control_params()
                if params.persona_modifier:
                    parts.append(params.persona_modifier)

            if history:
                lines = [f"{h['role']}: {h['text']}" for h in history[-self._max_history:]]
                parts.append("Previous conversation:\n" + "\n".join(lines))
            parts.append("Continue naturally.")
            context = "\n\n".join(parts)

            # Determine effective model: hormone-based or manual selection
            effective_model = self._current_model
            if self.hormones:
                params = self.hormones.get_control_params()
                effective_model = params.model

            async with message.channel.typing():
                try:
                    response = await self.executor.execute(
                        user_message, system_prompt=context,
                        model=MODEL_ALIASES[effective_model],
                    )
                except UsageLimitExceeded:
                    await asyncio.sleep(CONFIG["usage_limits"]["min_call_interval_seconds"])
                    response = await self.executor.execute(
                        user_message, system_prompt=context,
                        model=MODEL_ALIASES[effective_model],
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

            # Successful response → dopamine boost
            if self.hormones:
                self.hormones.trigger_dopamine(0.05)
        except Exception as e:
            await message.channel.send(f"Error: {e}")
            if self.hormones:
                self.hormones.trigger_cortisol(0.15)

    async def _analyze_sentiment(self, user_message: str):
        """Analyze message tone via haiku and trigger hormone changes."""
        if not self.hormones:
            return

        try:
            raw = await self.executor.execute(
                user_message,
                system_prompt=SENTIMENT_SYSTEM_PROMPT,
                model=MODEL_ALIASES["haiku"],
                session_id=f"sentiment-{uuid.uuid4()}",
            )
            # Strip markdown code fences if present
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            data = json.loads(text)
            dopamine_delta = max(-0.2, min(0.2, float(data.get("dopamine_delta", 0))))
            cortisol_delta = max(-0.2, min(0.2, float(data.get("cortisol_delta", 0))))

            if dopamine_delta:
                self.hormones.trigger_dopamine(dopamine_delta)
            if cortisol_delta:
                self.hormones.trigger_cortisol(cortisol_delta)

            print(f"Sentiment analysis: dopamine={dopamine_delta:+.2f}, cortisol={cortisol_delta:+.2f}")
        except Exception as e:
            # Sentiment failure must never block the main response
            print(f"Sentiment analysis skipped: {e}")

    async def _handle_model_command(self, message: discord.Message, content: str):
        """Handle !model command for switching available models."""
        parts = content.split()
        if len(parts) == 1:
            model_id = MODEL_ALIASES[self._current_model]
            available = ", ".join(
                f"{k} → `{v}`" for k, v in MODEL_ALIASES.items()
            )
            await message.channel.send(
                f"**Provider**: `{AI_PROVIDER}`\n"
                f"**Current model**: `{model_id}`\n"
                f"**Available**:\n{available}"
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
        await message.channel.send(
            f"Model switched to `{model_id}` (provider: `{AI_PROVIDER}`)"
        )

    async def _handle_hormones_command(self, message: discord.Message):
        """Handle !hormones command to show current hormone state."""
        if not self.hormones:
            await message.channel.send("Hormone system not active.")
            return

        status = self.hormones.get_status_dict()
        lines = [
            f"**Hormone Status** ({status['label']})",
            f"Dopamine: `{status['dopamine']:.3f}`",
            f"Cortisol: `{status['cortisol']:.3f}`",
            f"Energy: `{status['energy']:.3f}`",
            f"Ticks: `{status['tick_count']}`",
            f"Model: `{status['effective_model']}`",
        ]
        await message.channel.send("\n".join(lines))

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
