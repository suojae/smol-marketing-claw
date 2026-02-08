"""SNS (X / Threads) API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.x_client import XClient
from src.threads_client import ThreadsClient

sns_router = APIRouter(prefix="/sns", tags=["SNS"])

x_client = XClient()
threads_client = ThreadsClient()


class SNSPostRequest(BaseModel):
    text: str


class SNSReplyRequest(BaseModel):
    text: str
    post_id: str


class SNSPostResponse(BaseModel):
    success: bool
    post_id: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None


@sns_router.post("/x/post", response_model=SNSPostResponse)
async def x_post(req: SNSPostRequest):
    if not x_client.is_configured:
        raise HTTPException(status_code=503, detail="X API not configured")
    result = await x_client.post(req.text)
    return SNSPostResponse(**result.__dict__)


@sns_router.post("/x/reply", response_model=SNSPostResponse)
async def x_reply(req: SNSReplyRequest):
    if not x_client.is_configured:
        raise HTTPException(status_code=503, detail="X API not configured")
    result = await x_client.reply(req.text, req.post_id)
    return SNSPostResponse(**result.__dict__)


@sns_router.post("/threads/post", response_model=SNSPostResponse)
async def threads_post(req: SNSPostRequest):
    if not threads_client.is_configured:
        raise HTTPException(status_code=503, detail="Threads API not configured")
    result = await threads_client.post(req.text)
    return SNSPostResponse(**result.__dict__)


@sns_router.post("/threads/reply", response_model=SNSPostResponse)
async def threads_reply(req: SNSReplyRequest):
    if not threads_client.is_configured:
        raise HTTPException(status_code=503, detail="Threads API not configured")
    result = await threads_client.reply(req.text, req.post_id)
    return SNSPostResponse(**result.__dict__)
