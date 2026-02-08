"""Autonomous AI engine — makes decisions and acts proactively."""

import json
import subprocess
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

import aiohttp

from src.executor import ClaudeExecutor
from src.context import ContextCollector
from src.memory import GuardrailMemory
from src.config import CONFIG


class AutonomousEngine:
    """Autonomous AI Engine - makes decisions and acts proactively"""

    MAX_CALLS_PER_SESSION = 50

    def __init__(
        self,
        claude: ClaudeExecutor,
        context_collector: ContextCollector,
        memory: Optional[GuardrailMemory] = None,
        discord_bot=None,
    ):
        self.claude = claude
        self.context_collector = context_collector
        self.memory = memory or GuardrailMemory()
        self.discord_bot = discord_bot
        self.last_check = None
        self._session_id: Optional[str] = None
        self._session_call_count: int = 0

    def _get_or_reset_session(self) -> str:
        """Get current session ID, or create a new one if limit reached"""
        if (
            self._session_id is None
            or self._session_call_count >= self.MAX_CALLS_PER_SESSION
        ):
            self._session_id = str(uuid.uuid4())
            self._session_call_count = 0
            print(f"New session started: {self._session_id[:8]}... (limit: {self.MAX_CALLS_PER_SESSION} calls)")
        return self._session_id

    @property
    def is_first_call_in_session(self) -> bool:
        return self._session_call_count == 0

    def get_system_prompt(self) -> str:
        """Meta-prompt that gives AI autonomy"""
        return """You are an autonomous AI assistant.

Role:
- Judge and act autonomously without user commands
- Analyze provided context to decide necessary actions
- Proactively contact and suggest

Decision criteria:
1. Git changes -> suggest commit
2. TODOs exist -> check progress
3. Important time -> remind
4. Abandoned tasks -> notify

Response format:
- action: "none" | "notify" | "suggest" | "remind"
- message: message to user
- reasoning: why this action was taken

Respond in JSON format."""

    async def think(self, events: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
        """AI thinks autonomously and makes decisions"""
        print("\nAutonomous AI thinking...\n")

        # 1. Get or reset session
        session_id = self._get_or_reset_session()
        is_first = self.is_first_call_in_session

        # 2. Collect context
        context = await self.context_collector.collect()
        print(f"Context: {json.dumps(context, indent=2, ensure_ascii=False)}")

        # 3. Build git status string
        git_status = "none"
        if context["git"]:
            git_status = f"branch {context['git']['branch']}, "
            git_status += (
                "has changes" if context["git"]["hasChanges"] else "no changes"
            )

        # 3.5. Build event summary
        event_text = ""
        if events:
            event_lines = "\n".join([f"- [{e['type']}] {e['detail']}" for e in events])
            event_text = f"\nDetected events:\n{event_lines}\n"
            print(f"Events: {len(events)} detected")

        # 4. Build prompt (first call includes patterns, subsequent calls are lightweight)
        if is_first:
            memory_context = self.memory.get_context()
            safety_context = self.memory.get_safety_context()
            print("First call in session: including patterns + memory")

            prompt = f"""Current situation:

Time: {context['time']}
Git status: {git_status}
TODOs: {len(context['tasks'])}
{event_text}
{memory_context}

{safety_context}

Based on your judgment:
1. Is there anything to notify the user about?
2. Any suggestions?
3. Any reminders?

Check recent activity and avoid duplicate notifications.

Respond in JSON."""
        else:
            print(f"Session call {self._session_call_count + 1}/{self.MAX_CALLS_PER_SESSION}: context only")

            prompt = f"""Status update:

Time: {context['time']}
Git status: {git_status}
TODOs: {len(context['tasks'])}
{event_text}
Refer to previous conversation memory and patterns.
Respond in JSON."""

        try:
            response = await self.claude.execute(
                prompt,
                self.get_system_prompt() if is_first else None,
                session_id=session_id,
            )
            self._session_call_count += 1
            print(f"AI response: {response}")

            # Check usage warning and send Discord alert
            usage_warning = self.claude.usage_tracker.get_warning()
            if usage_warning:
                await self.notify_user(usage_warning)

            # 3. Parse JSON
            try:
                # Extract JSON from markdown code blocks
                if "```json" in response:
                    json_start = response.find("```json") + 7
                    json_end = response.find("```", json_start)
                    json_str = response[json_start:json_end].strip()
                elif "{" in response:
                    json_start = response.find("{")
                    json_end = response.rfind("}") + 1
                    json_str = response[json_start:json_end]
                else:
                    json_str = response

                decision = json.loads(json_str)
            except json.JSONDecodeError:
                print("JSON parse failed, treating as text")
                decision = {
                    "action": "none",
                    "message": response,
                    "reasoning": "JSON parse failed",
                }

            print(f"\nAI decision: {decision}")

            # 4. Check for duplicates
            message = decision.get("message", "")
            if decision.get("action") != "none" and message:
                if self.memory.should_skip_duplicate(message):
                    print("Skipping duplicate notification")
                    decision["action"] = "skipped"
                    decision["reasoning"] = "Duplicate notification (sent within 24h)"
                    self.memory.add_decision(decision)
                    self.last_check = datetime.now()
                    return decision

            # 5. Execute action
            if decision.get("action") != "none":
                await self.execute_action(decision)

            # 6. Save decision to memory
            self.memory.add_decision(decision)

            self.last_check = datetime.now()
            return decision

        except Exception as err:
            print(f"Error: {err}")
            return None

    async def execute_action(self, decision: Dict[str, Any]):
        """Execute the decided action"""
        action = decision.get("action")
        print(f"\nExecuting action: {action}\n")

        if action in ["notify", "suggest", "remind"]:
            await self.notify_user(decision.get("message", ""))

    async def notify_user(self, message: str):
        """Send notification to user"""
        print("Notifying user:")
        print("=" * 50)
        print(message)
        print("=" * 50)

        # Discord webhook notification
        if CONFIG.get("discord_webhook_url"):
            await self.send_discord_notification(message)

        # macOS notification (optional)
        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{message}" with title "AI Assistant"',
                ],
                check=False,
            )
        except Exception:
            pass

    async def send_discord_notification(self, message: str):
        """Send notification to Discord via webhook"""
        webhook_url = CONFIG.get("discord_webhook_url")
        if not webhook_url:
            return

        try:
            embed = {
                "title": "Smol Claw Alert",
                "description": message,
                "color": 16730939,  # Coral color (#FF6B6B)
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "Smol Claw - Your autonomous AI assistant"
                }
            }

            payload = {
                "username": "Smol Claw",
                "avatar_url": "https://raw.githubusercontent.com/suojae/smol-claw/main/.github/crayfish.svg",
                "embeds": [embed]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 204:
                        print("Discord notification sent!")
                    else:
                        print(f"Discord webhook returned status {response.status}")

        except Exception as e:
            print(f"Failed to send Discord notification: {e}")

        # Discord bot notification
        if self.discord_bot:
            await self.discord_bot.send_notification(message)
