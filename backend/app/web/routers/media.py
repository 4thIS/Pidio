# backend/app/web/routers/media.py
"""E-1 미디어 라우터 (Task 8.1) — media_repo 위임."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.domain import media_repo
from app.web.auth import require_session
from app.web.media_ops import remove_media_fully
from app.web.serializers import media_out

router = APIRouter(prefix="/api/media", tags=["media"], dependencies=[Depends(require_session)])


@router.get("")
def list_media(request: Request, type: str = "all") -> list[dict]:
    db = request.app.state.deps.db
    rows = media_repo.list_media(db, None if type == "all" else type)
    return [media_out(r) for r in rows]


class PatchBody(BaseModel):
    custom_title: str


@router.patch("/{content_id}")
def patch_media(content_id: str, body: PatchBody, request: Request) -> dict:
    db = request.app.state.deps.db
    media_repo.set_custom_title(db, content_id, body.custom_title)
    return {"ok": True}


@router.delete("/{content_id}")
def remove_media(content_id: str, request: Request) -> dict:
    deps = request.app.state.deps
    remove_media_fully(deps, content_id)
    # 라이브 재생 큐/플리/재생바 상태 방송
    request.app.state.hub.publish(deps.player.get_state())
    return {"ok": True}
