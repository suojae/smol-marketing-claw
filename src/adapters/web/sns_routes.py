"""SNS (X / Threads) API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.adapters.sns.x import XClient
from src.adapters.sns.threads import ThreadsClient
from src.config import CONFIG
from src.adapters.web.approval_queue import enqueue_post, approve_and_execute, reject, list_pending

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
    queued: Optional[bool] = None
    approval_id: Optional[str] = None


@sns_router.post("/x/post", response_model=SNSPostResponse)
async def x_post(req: SNSPostRequest):
    if CONFIG.get("require_manual_approval", True):
        return SNSPostResponse(**(await enqueue_post("x", "post", req.text)))
    if not x_client.is_configured:
        raise HTTPException(status_code=503, detail="X API not configured")
    result = await x_client.post(req.text)
    return SNSPostResponse(**result.__dict__)


@sns_router.post("/x/reply", response_model=SNSPostResponse)
async def x_reply(req: SNSReplyRequest):
    if CONFIG.get("require_manual_approval", True):
        return SNSPostResponse(**(await enqueue_post("x", "reply", req.text, meta={"tweet_id": req.post_id})))
    if not x_client.is_configured:
        raise HTTPException(status_code=503, detail="X API not configured")
    result = await x_client.reply(req.text, req.post_id)
    return SNSPostResponse(**result.__dict__)


@sns_router.post("/threads/post", response_model=SNSPostResponse)
async def threads_post(req: SNSPostRequest):
    if CONFIG.get("require_manual_approval", True):
        return SNSPostResponse(**(await enqueue_post("threads", "post", req.text)))
    if not threads_client.is_configured:
        raise HTTPException(status_code=503, detail="Threads API not configured")
    result = await threads_client.post(req.text)
    return SNSPostResponse(**result.__dict__)


@sns_router.post("/threads/reply", response_model=SNSPostResponse)
async def threads_reply(req: SNSReplyRequest):
    if CONFIG.get("require_manual_approval", True):
        return SNSPostResponse(**(await enqueue_post("threads", "reply", req.text, meta={"post_id": req.post_id})))
    if not threads_client.is_configured:
        raise HTTPException(status_code=503, detail="Threads API not configured")
    result = await threads_client.reply(req.text, req.post_id)
    return SNSPostResponse(**result.__dict__)


# --- Approval endpoints ---

class ApprovalRequest(BaseModel):
    id: str


@sns_router.get("/approvals/pending")
async def approvals_pending():
    return {"pending": list_pending()}


@sns_router.post("/approvals/approve")
async def approvals_approve(req: ApprovalRequest):
    return await approve_and_execute(req.id)


@sns_router.post("/approvals/reject")
async def approvals_reject(req: ApprovalRequest):
    return await reject(req.id)
