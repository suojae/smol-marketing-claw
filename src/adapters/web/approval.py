"""Manual approval queue for SNS posting.

Provides a simple, file‑backed queue so posts are never published
without an explicit human approval. Designed to be light‑touch and
work in both MCP tool path and FastAPI routes.

States: pending -> approved -> posted | failed
         \\-> rejected
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import CONFIG


MEMORY_DIR = Path("memory")
MEMORY_DIR.mkdir(exist_ok=True)
QUEUE_FILE = MEMORY_DIR / "post_approvals.jsonl"

# Protect concurrent JSONL reads/writes from MCP, Discord bot, and FastAPI
_file_lock = asyncio.Lock()


@dataclass
class PostApproval:
    id: str
    platform: str  # "threads" | "x" | "linkedin" | "instagram"
    action: str  # "post" | "reply"
    text: str
    meta: Dict[str, Any]
    status: str  # "pending" | "approved" | "rejected" | "posted" | "failed"
    created_at: str
    updated_at: str
    post_id: Optional[str] = None
    error: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_file():
    if not QUEUE_FILE.exists():
        QUEUE_FILE.touch()


def _append_record(rec: PostApproval) -> None:
    _ensure_file()
    with QUEUE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")


def _read_all() -> List[PostApproval]:
    _ensure_file()
    out: List[PostApproval] = []
    with QUEUE_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            out.append(PostApproval(**data))
    return out


def _write_all(recs: List[PostApproval]) -> None:
    tmp = QUEUE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    tmp.replace(QUEUE_FILE)


async def enqueue_post(platform: str, action: str, text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rec = PostApproval(
        id=str(uuid.uuid4())[:8],
        platform=platform,
        action=action,
        text=text,
        meta=meta or {},
        status="pending",
        created_at=_now_iso(),
        updated_at=_now_iso(),
    )
    async with _file_lock:
        _append_record(rec)
    return {"success": True, "queued": True, "approval_id": rec.id, "text": text}


def list_pending() -> List[Dict[str, Any]]:
    return [asdict(r) for r in _read_all() if r.status == "pending"]


def _update_status(rec_id: str, status: str, **kw) -> Optional[PostApproval]:
    recs = _read_all()
    found = None
    for r in recs:
        if r.id == rec_id:
            r.status = status
            r.updated_at = _now_iso()
            for k, v in kw.items():
                setattr(r, k, v)
            found = r
            break
    if found:
        _write_all(recs)
    return found


def _get_client(platform: str):
    """Return the singleton SNS client from AppState."""
    from server.state import get_state
    state = get_state()
    clients = {
        "x": state.x_client,
        "threads": state.threads_client,
        "linkedin": getattr(state, "linkedin_client", None),
        "instagram": getattr(state, "instagram_client", None),
    }
    client = clients.get(platform)
    if not client:
        raise ValueError(f"unsupported platform: {platform}")
    return client


async def approve_and_execute(rec_id: str) -> Dict[str, Any]:
    async with _file_lock:
        recs = _read_all()
        target = next((r for r in recs if r.id == rec_id), None)
        if not target:
            return {"success": False, "error": "not_found"}
        if target.status != "pending":
            return {"success": False, "error": f"invalid_status:{target.status}"}
        _update_status(rec_id, "approved")

    try:
        client = _get_client(target.platform)
        if target.action == "post":
            if target.platform == "instagram":
                image_url = target.meta.get("image_url", "")
                res = await client.post(target.text, image_url)
            else:
                res = await client.post(target.text)
        elif target.action == "reply":
            reply_id = target.meta.get("tweet_id") or target.meta.get("post_id", "")
            res = await client.reply(target.text, reply_id)
        else:
            raise ValueError(f"unsupported action: {target.action}")

        if res.success:
            async with _file_lock:
                _update_status(rec_id, "posted", post_id=res.post_id)
            return {"success": True, "post_id": res.post_id, "text": target.text}
        else:
            async with _file_lock:
                _update_status(rec_id, "failed", error=res.error)
            return {"success": False, "error": res.error}
    except Exception as e:
        async with _file_lock:
            _update_status(rec_id, "failed", error=str(e))
        return {"success": False, "error": str(e)}


async def reject(rec_id: str) -> Dict[str, Any]:
    async with _file_lock:
        updated = _update_status(rec_id, "rejected")
    if not updated:
        return {"success": False, "error": "not_found"}
    return {"success": True}

