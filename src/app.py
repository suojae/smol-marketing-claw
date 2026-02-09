"""FastAPI application, routes, models, and startup."""

import asyncio
import os
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import src.config as _config
from src.config import CONFIG
from src.context import ContextCollector
from src.executor import ClaudeExecutor
from src.discord_bot import DiscordBot
from src.engine import AutonomousEngine
from src.watcher import start_file_watcher
from src.sns_routes import sns_router
from src.persona import BOT_PERSONA

app = FastAPI(title="Autonomous AI Server")
app.include_router(sns_router)

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
    usage: Optional[Dict[str, Any]] = None


class ThinkResponse(BaseModel):
    decision: Optional[Dict[str, Any]]


# API endpoints
@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """Manual question endpoint"""
    try:
        response = await claude.execute(request.message, system_prompt=BOT_PERSONA)
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
        usage=claude.usage_tracker.get_status(),
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
        else "N/A"
    )

    usage = claude.usage_tracker.get_status()

    return f"""
    <html>
      <head>
        <title>Autonomous AI Server</title>
        <style>
          body {{ font-family: monospace; max-width: 800px; margin: 50px auto; }}
          .status {{ background: #e8f5e9; padding: 20px; border-radius: 5px; }}
          .usage {{ background: #fff3e0; padding: 20px; border-radius: 5px; margin-top: 10px; }}
          .usage-bar {{ background: #e0e0e0; border-radius: 4px; height: 20px; margin: 5px 0; }}
          .usage-bar-fill {{ background: #ff6b6b; height: 100%; border-radius: 4px; }}
          button {{ padding: 10px 20px; font-size: 16px; margin: 5px; }}
        </style>
      </head>
      <body>
        <h1>Autonomous AI Server</h1>

        <div class="status">
          <p><strong>Session:</strong> {CONFIG["session_id"]}</p>
          <p><strong>Autonomous mode:</strong> {'enabled' if CONFIG["autonomous_mode"] else 'disabled'}</p>
          <p><strong>Last check:</strong> {last_check}</p>
        </div>

        <div class="usage">
          <h3>Usage</h3>
          <p><strong>Today:</strong> {usage["calls_today"]}/{usage["limits"]["per_day"]}</p>
          <div class="usage-bar">
            <div class="usage-bar-fill" style="width: {min(usage["calls_today"] * 100 // max(usage["limits"]["per_day"], 1), 100)}%"></div>
          </div>
          <p><strong>This hour:</strong> {usage["calls_this_hour"]}/{usage["limits"]["per_hour"]}</p>
          <p><strong>Total:</strong> {usage["total_calls_all_time"]}</p>
          <p><strong>Status:</strong> {'paused' if usage["paused"] else 'active'}</p>
        </div>

        <h2>Manual trigger</h2>
        <button onclick="think()">Think now</button>
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
    """Queue-based event consumer — blocks until events arrive, zero polling"""
    print("Event-driven autonomous loop started (queue consumer)")

    # Event-driven loop — blocks on queue.get(), wakes only on real events
    while True:
        try:
            first_event = await _config.event_queue.get()
            events = [first_event]
            # Drain any additional queued events
            while not _config.event_queue.empty():
                events.append(_config.event_queue.get_nowait())
            event_types = [e["type"] for e in events]
            print(f"Events received: {event_types}")
            await autonomous_engine.think(events=events)
        except Exception as e:
            print(f"Error in event loop: {e}")


@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    print("Autonomous AI server starting")
    print(f"Session: {CONFIG['session_id']}")
    print(f"Autonomous mode: {'enabled' if CONFIG['autonomous_mode'] else 'disabled'}")

    # Re-create event_queue on the running event loop
    _config.event_queue = asyncio.Queue()

    if CONFIG["autonomous_mode"]:
        print("File watcher (event push, no timer)")

        # Start OS-level file watcher (push-based)
        loop = asyncio.get_event_loop()
        start_file_watcher(loop)

        # Start queue consumer
        asyncio.create_task(autonomous_loop())

    # Start Discord bot if configured
    if discord_bot:
        token = os.getenv("DISCORD_BOT_TOKEN", "")
        print("Starting Discord bot...")

        async def _start_discord():
            try:
                await discord_bot.start(token)
            except Exception as e:
                print(f"Discord bot failed to start: {e}")

        asyncio.create_task(_start_discord())
    else:
        print("Discord bot not configured (set DISCORD_BOT_TOKEN in .env)")

    print("Ready!")
