# backend/app/web/routers/settings.py
"""E-5 설정 라우터 & 스캔 트리거 (Task 8.5)."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.domain import scanner
from app.web.auth import (
    get_setting,
    hash_password,
    require_session,
    set_setting,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["settings"], dependencies=[Depends(require_session)])

_PHOTO_DEFAULT = 5


@router.get("/settings")
def get_settings(request: Request) -> dict:
    db = request.app.state.deps.db
    dpid = get_setting(db, "default_playlist_id")
    psec = get_setting(db, "photo_default_sec")
    return {
        "default_playlist_id": int(dpid) if dpid else None,
        "photo_default_sec": int(psec) if psec else _PHOTO_DEFAULT,
    }


class SettingsBody(BaseModel):
    default_playlist_id: int | None = None
    photo_default_sec: int = _PHOTO_DEFAULT


@router.put("/settings")
def put_settings(body: SettingsBody, request: Request) -> dict:
    db = request.app.state.deps.db
    set_setting(db, "default_playlist_id", "" if body.default_playlist_id is None else str(body.default_playlist_id))
    set_setting(db, "photo_default_sec", str(body.photo_default_sec))
    return {"ok": True}


class PasswordBody(BaseModel):
    old: str
    new: str


@router.post("/settings/password")
def change_password(body: PasswordBody, request: Request) -> dict:
    db = request.app.state.deps.db
    stored = get_setting(db, "password_hash")
    if stored is None or not verify_password(body.old, stored):
        raise HTTPException(status_code=401, detail="현재 비밀번호가 올바르지 않습니다")
    set_setting(db, "password_hash", hash_password(body.new))
    return {"ok": True}


@router.post("/rescan")
def rescan(request: Request) -> dict:
    deps = request.app.state.deps
    if not os.path.isdir(deps.media_root):
        raise HTTPException(status_code=409, detail="USB 미마운트")
    result = scanner.scan_library(deps.db, deps.media_root)
    return result
