"""FastAPI application — multi-bot launcher + SNS API routes."""

import asyncio
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.config import CONFIG, AI_PROVIDER
from src.executor import create_executor
from src.sns_routes import sns_router
from src.persona import BOT_PERSONA

app = FastAPI(title="Smol Claw Marketing Server")
app.include_router(sns_router)

# Global executor
executor = create_executor(AI_PROVIDER)


# Request/Response models
class AskRequest(BaseModel):
    message: str


class AskResponse(BaseModel):
    response: str


class StatusResponse(BaseModel):
    sessionId: str
    aiProvider: str
    usage: Optional[Dict[str, Any]] = None


# API endpoints
@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """Manual question endpoint"""
    try:
        response = await executor.execute(request.message, system_prompt=BOT_PERSONA)
        return AskResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=StatusResponse)
async def status():
    """Server status endpoint"""
    return StatusResponse(
        sessionId=CONFIG["session_id"],
        aiProvider=AI_PROVIDER,
        usage=executor.usage_tracker.get_status(),
    )


@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "session": CONFIG["session_id"], "provider": AI_PROVIDER}


@app.on_event("startup")
async def startup_event():
    """Start multi-bot system on server startup."""
    print("Smol Claw Marketing Server starting")
    print(f"Session: {CONFIG['session_id']}")

    from src.config import DISCORD_TOKENS
    has_multi_bot = any(DISCORD_TOKENS.values())

    if has_multi_bot:
        from src.bots.launcher import launch_all_bots
        print("Starting multi-bot system...")

        async def _start_multi_bots():
            try:
                await launch_all_bots()
            except Exception as e:
                print(f"Multi-bot system failed to start: {e}")

        asyncio.create_task(_start_multi_bots())
    else:
        print("Discord bots not configured (set DISCORD_*_TOKEN in .env)")

    print("Ready!")
