# backend/app/web/routers/schedule.py
"""E-3 예약 라우터 (Task 8.3) — 같은 타입 겹침 시 409."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.domain import playlist_repo
from app.domain.playlist_repo import ScheduleConflict
from app.web.auth import require_session

router = APIRouter(prefix="/api/playlists", tags=["schedule"], dependencies=[Depends(require_session)])


class ScheduleBody(BaseModel):
    sched_type: str
    weekdays: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    start_dt: str | None = None
    end_dt: str | None = None


@router.put("/{playlist_id}/schedule")
def set_schedule(playlist_id: int, body: ScheduleBody, request: Request) -> dict:
    db = request.app.state.deps.db
    try:
        playlist_repo.set_schedule(db, playlist_id, body.model_dump())
    except ScheduleConflict as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"ok": True}


@router.delete("/{playlist_id}/schedule")
def delete_schedule(playlist_id: int, request: Request) -> dict:
    playlist_repo.delete_schedule(request.app.state.deps.db, playlist_id)
    return {"ok": True}
