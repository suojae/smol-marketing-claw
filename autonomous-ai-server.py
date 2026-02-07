#!/usr/bin/env python3
"""
Autonomous AI Server (자율 AI 서버)

Features:
- AI judges autonomously
- Proactively contacts user
- Context-based behavior

Same autonomy as OpenClaw!
"""

import asyncio
import subprocess
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

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
                timeout=5
            ).strip()

            # Get git status
            status = subprocess.check_output(
                ["git", "status", "--short"],
                cwd=git_dir,
                encoding="utf-8",
                timeout=5
            ).strip()

            # Get last commit
            last_commit = subprocess.check_output(
                ["git", "log", "-1", "--oneline"],
                cwd=git_dir,
                encoding="utf-8",
                timeout=5
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

    def __init__(self, session_id: str):
        self.session_id = session_id

    async def execute(
        self,
        message: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Execute Claude CLI command"""
        print(f"[{datetime.now().isoformat()}] 📤 Executing")

        args = [
            "claude",
            "--print",
            "--session-id", self.session_id,
            "--permission-mode", "dontAsk",
            "--output-format", "text",
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
                timeout=60.0
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
# Autonomous Engine (핵심!)
# ============================================
class AutonomousEngine:
    """Autonomous AI Engine - makes decisions and acts proactively"""

    def __init__(self, claude: ClaudeExecutor, context_collector: ContextCollector):
        self.claude = claude
        self.context_collector = context_collector
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

        # 2. Ask AI to judge
        git_status = "없음"
        if context["git"]:
            git_status = f"브랜치 {context['git']['branch']}, "
            git_status += "변경사항 있음" if context["git"]["hasChanges"] else "변경사항 없음"

        prompt = f"""현재 상황:

시간: {context['time']}
Git 상태: {git_status}
할 일: {len(context['tasks'])}개

지금 당신이 판단하기에:
1. 사용자에게 알려야 할 것이 있나요?
2. 제안할 것이 있나요?
3. 리마인드할 것이 있나요?

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
                    "reasoning": "JSON 파싱 실패"
                }

            print(f"\n✅ AI 결정: {decision}")

            # 4. Execute action
            if decision.get("action") != "none":
                await self.execute_action(decision)

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
            subprocess.run([
                "osascript", "-e",
                f'display notification "{message}" with title "AI 비서"'
            ], check=False)
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


# ============================================
# FastAPI Server
# ============================================
app = FastAPI(title="Autonomous AI Server")

# Global instances
claude = ClaudeExecutor(CONFIG["session_id"])
context_collector = ContextCollector()
autonomous_engine = AutonomousEngine(claude, context_collector)

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
        lastCheck=autonomous_engine.last_check.isoformat()
            if autonomous_engine.last_check else None
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
    last_check = autonomous_engine.last_check.isoformat() \
        if autonomous_engine.last_check else "없음"

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

    print("✅ 준비 완료!")
    print("AI가 스스로 판단하고 먼저 연락합니다.\n")


# ============================================
# Main entry point
# ============================================
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=CONFIG["port"],
        log_level="info"
    )
