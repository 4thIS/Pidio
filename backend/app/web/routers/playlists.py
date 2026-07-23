# backend/app/web/routers/playlists.py
"""E-2 플레이리스트 라우터 (Task 8.2) — playlist_repo + AppService 위임."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.domain import playlist_repo
from app.web.auth import require_session

router = APIRouter(prefix="/api/playlists", tags=["playlists"], dependencies=[Depends(require_session)])


def _db(request):
    return request.app.state.deps.db


@router.get("")
def list_playlists(request: Request) -> list[dict]:
    return playlist_repo.list_playlists(_db(request))


class CreateBody(BaseModel):
    name: str


@router.post("")
def create_playlist(body: CreateBody, request: Request) -> dict:
    pid = playlist_repo.create_playlist(_db(request), body.name)
    return {"id": pid}


@router.get("/{playlist_id}")
def get_playlist(playlist_id: int, request: Request) -> dict:
    pl = playlist_repo.get_playlist(_db(request), playlist_id)
    if pl is None:
        raise HTTPException(status_code=404, detail="not found")
    return pl


class UpdateBody(BaseModel):
    name: str
    repeat_mode: str = "off"
    shuffle: bool = False
    blocks: list[dict] = []


@router.put("/{playlist_id}")
def update_playlist(playlist_id: int, body: UpdateBody, request: Request) -> dict:
    playlist_repo.update_playlist(
        _db(request), playlist_id, body.name, body.repeat_mode, body.shuffle, body.blocks
    )
    return {"ok": True}


@router.delete("/{playlist_id}")
def delete_playlist(playlist_id: int, request: Request) -> dict:
    playlist_repo.delete_playlist(_db(request), playlist_id)
    return {"ok": True}


@router.post("/{playlist_id}/play")
def play_playlist(playlist_id: int, request: Request) -> dict:
    deps = request.app.state.deps
    if playlist_repo.get_playlist(deps.db, playlist_id) is None:
        raise HTTPException(status_code=404, detail="not found")
    deps.service.play_playlist(playlist_id, manual=True)
    request.app.state.hub.publish(deps.player.get_state())
    return {"ok": True}
