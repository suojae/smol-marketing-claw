#!/usr/bin/env python3
"""
Autonomous AI Server (자율 AI 서버)

Features:
- AI judges autonomously
- Proactively contacts user
- Context-based behavior

Same autonomy as OpenClaw!
"""

__version__ = "0.0.1"

import asyncio
import subprocess
import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import Counter

import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import discord
from dotenv import load_dotenv

load_dotenv()

# ============================================
# Configuration
# ============================================
CONFIG = {
    "port": 3000,
    "session_id": str(uuid.uuid4()),
    "check_interval": 30 * 60,  # 30 minutes in seconds
    "autonomous_mode": True,
    "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", ""),  # Set via environment variable
}


# ============================================
# Context Collector (AI에게 정보 제공)
# ============================================
class ContextCollector:
    """Collects context information for AI decision making"""

    async def collect(self) -> Dict[str, Any]:
        """Collect all context information"""
        context = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": await self.get_system_info(),
            "git": await self.get_git_info(),
            "tasks": await self.get_tasks(),
            "calendar": await self.get_calendar(),
        }
        return context

    async def get_system_info(self) -> Optional[Dict[str, Any]]:
        """Get system information"""
        try:
            return {
                "platform": os.sys.platform,
                "cwd": os.getcwd(),
            }
        except Exception:
            return None

    async def get_git_info(self) -> Optional[Dict[str, Any]]:
        """Get git repository information"""
        try:
            git_dir = Path.home() / "Documents"

            # Get current branch
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=git_dir,
                encoding="utf-8",
                timeout=5,
            ).strip()

            # Get git status
            status = subprocess.check_output(
                ["git", "status", "--short"], cwd=git_dir, encoding="utf-8", timeout=5
            ).strip()

            # Get last commit
            last_commit = subprocess.check_output(
                ["git", "log", "-1", "--oneline"],
                cwd=git_dir,
                encoding="utf-8",
                timeout=5,
            ).strip()

            return {
                "branch": branch,
                "status": status,
                "lastCommit": last_commit,
                "hasChanges": len(status) > 0,
            }
        except Exception:
            return None

    async def get_tasks(self) -> List[str]:
        """Get TODO tasks"""
        try:
            todo_path = Path.home() / "todo.txt"
            if todo_path.exists():
                content = todo_path.read_text(encoding="utf-8")
                return [line for line in content.split("\n") if line.strip()]
            return []
        except Exception:
            return []

    async def get_calendar(self) -> List[Any]:
        """Get calendar events (optional)"""
        # TODO: Integrate with calendar API
        return []


# ============================================
# Claude Executor
# ============================================
class ClaudeExecutor:
    """Executes Claude CLI commands"""

    def __init__(self):
        pass

    async def execute(self, message: str, system_prompt: Optional[str] = None) -> str:
        """Execute Claude CLI command"""
        print(f"[{datetime.now().isoformat()}] 📤 Executing")

        args = [
            "claude",
            "--print",
            "--session-id",
            str(uuid.uuid4()),
            "--permission-mode",
            "bypassPermissions",
            "--output-format",
            "text",
        ]

        if system_prompt:
            args.extend(["--system-prompt", system_prompt])

        args.append(message)

        try:
            # Run with timeout
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=60.0,
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                print(f"[{datetime.now().isoformat()}] 📥 Completed")
                return stdout.decode("utf-8").strip()
            else:
                raise Exception(f"Exit code {result.returncode}: {stderr.decode()}")

        except asyncio.TimeoutError:
            raise Exception("Timeout")


# ============================================
# Memory Management (메모리 관리) 🦞
# ============================================
class SimpleMemory:
    """Simple JSON-based memory management with no external dependencies"""

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.max_decisions = 100
        self.decisions_file = self.memory_dir / "decisions.json"
        self.summary_file = self.memory_dir / "summary.txt"

    def load_decisions(self) -> List[Dict[str, Any]]:
        """Load decisions from JSON file"""
        if not self.decisions_file.exists():
            return []
        try:
            with open(self.decisions_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load decisions: {e}")
            return []

    def save_decisions(self, decisions: List[Dict[str, Any]]):
        """Save decisions to JSON file"""
        try:
            with open(self.decisions_file, "w", encoding="utf-8") as f:
                json.dump(decisions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Failed to save decisions: {e}")

    def load_summary(self) -> str:
        """Load summary from text file"""
        if not self.summary_file.exists():
            return "No previous activity."
        try:
            return self.summary_file.read_text(encoding="utf-8")
        except Exception:
            return "No previous activity."

    def save_summary(self, summary: str):
        """Save summary to text file"""
        try:
            self.summary_file.write_text(summary, encoding="utf-8")
        except Exception as e:
            print(f"⚠️ Failed to save summary: {e}")

    def add_decision(self, decision: Dict[str, Any]):
        """Add a new decision and auto-manage memory"""
        decisions = self.load_decisions()

        # Add new decision with metadata
        decision_entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            **decision
        }
        decisions.append(decision_entry)

        # If exceeded max, create summary of old decisions
        if len(decisions) > self.max_decisions:
            old_decisions = decisions[:50]
            decisions = decisions[50:]

            # Create simple summary
            summary = self._create_summary(old_decisions)
            self.save_summary(summary)
            print(f"📝 Created summary of {len(old_decisions)} old decisions")

        self.save_decisions(decisions)

    def _create_summary(self, decisions: List[Dict[str, Any]]) -> str:
        """Create a simple text summary of decisions"""
        if not decisions:
            return "No previous activity."

        total = len(decisions)
        actions = Counter([d.get("action", "unknown") for d in decisions])
        first_date = decisions[0].get("timestamp", "unknown")
        last_date = decisions[-1].get("timestamp", "unknown")

        summary = f"""Summary of {total} decisions ({first_date} to {last_date}):
- Total actions: {total}
- Action breakdown: {dict(actions)}
- Most common action: {actions.most_common(1)[0][0] if actions else 'none'}
"""
        return summary

    def get_context(self) -> str:
        """Get memory context for AI"""
        summary = self.load_summary()
        recent = self.load_decisions()[-10:]  # Last 10 decisions

        if not recent:
            return "[Memory] No recent activity."

        recent_text = "\n".join([
            f"- [{d.get('timestamp', 'unknown')}] {d.get('action', 'unknown')}: {d.get('message', 'N/A')[:50]}"
            for d in recent
        ])

        return f"""[Long-term Memory]
{summary}

[Recent Activity (Last 10)]
{recent_text}
"""

    def should_skip_duplicate(self, message: str) -> bool:
        """Check if this message was sent recently (24h window)"""
        decisions = self.load_decisions()
        yesterday = datetime.now() - timedelta(days=1)

        for d in decisions:
            try:
                decision_time = datetime.fromisoformat(d.get("timestamp", ""))
                if decision_time > yesterday:
                    prev_message = d.get("message", "")
                    if self._similarity(message, prev_message) > 0.85:
                        print(f"⏭️  Skipping duplicate: '{message[:50]}...'")
                        return True
            except Exception:
                continue

        return False

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Calculate simple word-based similarity"""
        if not a or not b:
            return 0.0

        words_a = set(a.lower().split())
        words_b = set(b.lower().split())

        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b

        return len(intersection) / len(union)


class GuardrailMemory(SimpleMemory):
    """Security-focused memory - Smol Claw's differentiator! 🦞"""

    def __init__(self, memory_dir: str = "memory"):
        super().__init__(memory_dir)
        self.violations_file = self.memory_dir / "guardrail_violations.json"

    def load_violations(self) -> List[Dict[str, Any]]:
        """Load guardrail violations"""
        if not self.violations_file.exists():
            return []
        try:
            with open(self.violations_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_violations(self, violations: List[Dict[str, Any]]):
        """Save guardrail violations"""
        try:
            with open(self.violations_file, "w", encoding="utf-8") as f:
                json.dump(violations, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Failed to save violations: {e}")

    def record_violation(self, violation_type: str, target: str, reason: str):
        """Record a guardrail violation"""
        violations = self.load_violations()

        violation_entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "type": violation_type,
            "target": target,
            "reason": reason,
            "blocked": True
        }

        violations.append(violation_entry)
        self.save_violations(violations)

        print(f"🛡️  Guardrail violation recorded: {violation_type} on {target}")

    def get_safety_context(self) -> str:
        """Get security context for AI"""
        violations = self.load_violations()

        if not violations:
            return "[Security] No violations recorded. ✅"

        # Get recent violations (last 20)
        recent = violations[-20:]

        # Find patterns
        frequent_targets = Counter([v.get("target") for v in recent])
        frequent_types = Counter([v.get("type") for v in recent])

        safety_text = f"""[Security History] 🛡️
Total violations blocked: {len(violations)}
Recent violations: {len(recent)}

Most frequently attempted:
{chr(10).join([f'  - {target}: {count} times' for target, count in frequent_targets.most_common(3)])}

Violation types:
{chr(10).join([f'  - {vtype}: {count} times' for vtype, count in frequent_types.most_common(3)])}

⚠️ Be extra careful with these targets!
"""
        return safety_text


# ============================================
# Discord Bot
# ============================================
class DiscordBot(discord.Client):
    """Discord bot for bidirectional communication with users"""

    def __init__(self, claude: ClaudeExecutor):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.claude = claude
        self.notification_channel: Optional[discord.TextChannel] = None
        self.channel_id = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

    async def on_ready(self):
        print(f"🤖 Discord 봇 로그인: {self.user}")
        if self.channel_id:
            self.notification_channel = self.get_channel(self.channel_id)
            if self.notification_channel:
                print(f"📢 알림 채널: #{self.notification_channel.name}")
            else:
                print(f"⚠️ 채널 ID {self.channel_id}를 찾을 수 없습니다")

    async def on_message(self, message: discord.Message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Only respond in the configured channel
        if self.channel_id and message.channel.id != self.channel_id:
            return

        user_message = message.content
        print(f"💬 Discord 메시지 수신: {user_message}")

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
                    f"🛡️ 보안 가드레일: `{pattern}` 패턴이 감지되어 차단되었습니다."
                )
                print(f"🛡️ Guardrail blocked: {pattern}")
                return

        try:
            async with message.channel.typing():
                response = await self.claude.execute(user_message)

            # Split long messages (Discord 2000 char limit)
            for chunk in self._split_message(response):
                await message.channel.send(chunk)
        except Exception as e:
            await message.channel.send(f"오류가 발생했습니다: {e}")

    async def send_notification(self, message: str):
        """Send a notification message to the configured channel"""
        if not self.notification_channel:
            print("⚠️ Discord 알림 채널이 설정되지 않았습니다")
            return

        try:
            for chunk in self._split_message(message):
                await self.notification_channel.send(chunk)
            print("📨 Discord 알림 전송 완료")
        except Exception as e:
            print(f"❌ Discord 알림 전송 실패: {e}")

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


# ============================================
# Autonomous Engine (핵심!)
# ============================================
class AutonomousEngine:
    """Autonomous AI Engine - makes decisions and acts proactively"""

    def __init__(
        self,
        claude: ClaudeExecutor,
        context_collector: ContextCollector,
        memory: Optional[GuardrailMemory] = None,
        discord_bot: Optional["DiscordBot"] = None
    ):
        self.claude = claude
        self.context_collector = context_collector
        self.memory = memory or GuardrailMemory()
        self.discord_bot = discord_bot
        self.last_check = None

    def get_system_prompt(self) -> str:
        """Meta-prompt that gives AI autonomy"""
        return """당신은 자율 AI 비서입니다.

역할:
- 사용자가 명령하지 않아도 스스로 판단하고 행동
- 제공된 컨텍스트를 분석하여 필요한 일 결정
- 먼저 연락하고 제안

판단 기준:
1. Git 변경사항이 있으면 → 커밋 제안
2. TODO가 있으면 → 진행 상황 체크
3. 중요한 시간대 → 리마인드
4. 오래 방치된 작업 → 알림

응답 형식:
- action: "none" | "notify" | "suggest" | "remind"
- message: 사용자에게 보낼 메시지 (한국어)
- reasoning: 왜 이 행동을 했는지

반드시 JSON 형식으로 응답하세요."""

    async def think(self) -> Optional[Dict[str, Any]]:
        """AI thinks autonomously and makes decisions"""
        print("\n🧠 자율 AI 사고 중...\n")

        # 1. Collect context
        context = await self.context_collector.collect()
        print(f"📊 컨텍스트: {json.dumps(context, indent=2, ensure_ascii=False)}")

        # 2. Get memory context
        memory_context = self.memory.get_context()
        safety_context = self.memory.get_safety_context()
        print(f"🧠 메모리 컨텍스트 로드됨")

        # 3. Ask AI to judge
        git_status = "없음"
        if context["git"]:
            git_status = f"브랜치 {context['git']['branch']}, "
            git_status += (
                "변경사항 있음" if context["git"]["hasChanges"] else "변경사항 없음"
            )

        prompt = f"""현재 상황:

시간: {context['time']}
Git 상태: {git_status}
할 일: {len(context['tasks'])}개

{memory_context}

{safety_context}

지금 당신이 판단하기에:
1. 사용자에게 알려야 할 것이 있나요?
2. 제안할 것이 있나요?
3. 리마인드할 것이 있나요?

⚠️ 주의: 최근 활동을 확인하고 중복된 알림은 하지 마세요.

스스로 판단해서 JSON으로 응답하세요."""

        try:
            response = await self.claude.execute(prompt, self.get_system_prompt())
            print(f"🤖 AI 응답: {response}")

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
                print("⚠️ JSON 파싱 실패, 텍스트로 처리")
                decision = {
                    "action": "none",
                    "message": response,
                    "reasoning": "JSON 파싱 실패",
                }

            print(f"\n✅ AI 결정: {decision}")

            # 4. Check for duplicates
            message = decision.get("message", "")
            if decision.get("action") != "none" and message:
                if self.memory.should_skip_duplicate(message):
                    print("⏭️  Skipping duplicate notification")
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
            print(f"❌ 오류: {err}")
            return None

    async def execute_action(self, decision: Dict[str, Any]):
        """Execute the decided action"""
        action = decision.get("action")
        print(f"\n🎬 행동 실행: {action}\n")

        if action in ["notify", "suggest", "remind"]:
            await self.notify_user(decision.get("message", ""))

    async def notify_user(self, message: str):
        """Send notification to user"""
        print("📢 사용자에게 알림:")
        print("━" * 50)
        print(message)
        print("━" * 50)

        # Discord webhook notification 🦞
        if CONFIG.get("discord_webhook_url"):
            await self.send_discord_notification(message)

        # macOS notification (optional)
        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{message}" with title "AI 비서"',
                ],
                check=False,
            )
        except Exception:
            pass

    async def send_discord_notification(self, message: str):
        """Send notification to Discord via webhook 🦞"""
        webhook_url = CONFIG.get("discord_webhook_url")
        if not webhook_url:
            return

        try:
            embed = {
                "title": "🦞 Smol Claw Alert",
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
                        print("✅ Discord notification sent! 🦞")
                    else:
                        print(f"⚠️ Discord webhook returned status {response.status}")

        except Exception as e:
            print(f"❌ Failed to send Discord notification: {e}")

        # Discord bot notification
        if self.discord_bot:
            await self.discord_bot.send_notification(message)


# ============================================
# FastAPI Server
# ============================================
app = FastAPI(title="Autonomous AI Server")

# Global instances
claude = ClaudeExecutor()
context_collector = ContextCollector()
discord_bot: Optional[DiscordBot] = None

# Initialize Discord bot if token is configured
_discord_token = os.getenv("DISCORD_BOT_TOKEN", "")
if _discord_token and _discord_token != "your_token_here":
    discord_bot = DiscordBot(claude)

autonomous_engine = AutonomousEngine(claude, context_collector, discord_bot=discord_bot)


# Request/Response models
class AskRequest(BaseModel):
    message: str


class AskResponse(BaseModel):
    response: str


class StatusResponse(BaseModel):
    sessionId: str
    autonomousMode: bool
    lastCheck: Optional[str]


class ThinkResponse(BaseModel):
    decision: Optional[Dict[str, Any]]


# API endpoints
@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """Manual question endpoint"""
    try:
        response = await claude.execute(request.message)
        return AskResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=StatusResponse)
async def status():
    """Server status endpoint"""
    return StatusResponse(
        sessionId=CONFIG["session_id"],
        autonomousMode=CONFIG["autonomous_mode"],
        lastCheck=(
            autonomous_engine.last_check.isoformat()
            if autonomous_engine.last_check
            else None
        ),
    )


@app.get("/think", response_model=ThinkResponse)
async def think():
    """Manual think trigger endpoint"""
    try:
        decision = await autonomous_engine.think()
        return ThinkResponse(decision=decision)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def root():
    """Web dashboard"""
    last_check = (
        autonomous_engine.last_check.isoformat()
        if autonomous_engine.last_check
        else "없음"
    )

    return f"""
    <html>
      <head>
        <title>자율 AI 서버</title>
        <style>
          body {{ font-family: monospace; max-width: 800px; margin: 50px auto; }}
          .status {{ background: #e8f5e9; padding: 20px; border-radius: 5px; }}
          button {{ padding: 10px 20px; font-size: 16px; margin: 5px; }}
        </style>
      </head>
      <body>
        <h1>🧠 자율 AI 서버</h1>

        <div class="status">
          <p><strong>Session:</strong> {CONFIG["session_id"]}</p>
          <p><strong>자율 모드:</strong> {'활성화' if CONFIG["autonomous_mode"] else '비활성화'}</p>
          <p><strong>마지막 체크:</strong> {last_check}</p>
        </div>

        <h2>수동 트리거</h2>
        <button onclick="think()">🧠 지금 생각하기</button>
        <pre id="result"></pre>

        <script>
          async function think() {{
            const res = await fetch('/think');
            const data = await res.json();
            document.getElementById('result').textContent =
              JSON.stringify(data, null, 2);
          }}
        </script>
      </body>
    </html>
    """


# ============================================
# Background autonomous loop
# ============================================
async def autonomous_loop():
    """Background task that runs autonomous thinking periodically"""
    print("⏰ 자율 루프 시작")

    # Initial delay
    await asyncio.sleep(5)

    # First run
    await autonomous_engine.think()

    # Periodic runs
    while True:
        await asyncio.sleep(CONFIG["check_interval"])
        await autonomous_engine.think()


@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    print("🚀 자율 AI 서버 시작")
    print(f"📍 Session: {CONFIG['session_id']}")
    print(f"🧠 자율 모드: {'활성화' if CONFIG['autonomous_mode'] else '비활성화'}")

    if CONFIG["autonomous_mode"]:
        print(f"⏰ {CONFIG['check_interval'] // 60}분마다 자율 체크")
        asyncio.create_task(autonomous_loop())

    # Start Discord bot if configured
    if discord_bot:
        token = os.getenv("DISCORD_BOT_TOKEN", "")
        print("🤖 Discord 봇 시작 중...")

        async def _start_discord():
            try:
                await discord_bot.start(token)
            except Exception as e:
                print(f"❌ Discord 봇 시작 실패: {e}")

        asyncio.create_task(_start_discord())
    else:
        print("ℹ️ Discord 봇 미설정 (DISCORD_BOT_TOKEN을 .env에 설정하세요)")

    print("✅ 준비 완료!")
    print("AI가 스스로 판단하고 먼저 연락합니다.\n")


# ============================================
# Main entry point
# ============================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=CONFIG["port"], log_level="info")
