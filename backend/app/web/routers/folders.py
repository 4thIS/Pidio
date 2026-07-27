# backend/app/web/routers/folders.py
"""폴더 라우터 — 전체목록의 수동 그룹(태그식) 관리."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.domain import folder_repo
from app.web.auth import require_session
from app.web.media_ops import remove_media_fully

router = APIRouter(prefix="/api/folders", tags=["folders"], dependencies=[Depends(require_session)])


@router.get("")
def list_folders(request: Request) -> list[dict]:
    return folder_repo.list_folders(request.app.state.deps.db)


class CreateBody(BaseModel):
    name: str = "새 폴더"


@router.post("")
def create_folder(body: CreateBody, request: Request) -> dict:
    fid = folder_repo.create_folder(request.app.state.deps.db, body.name.strip() or "새 폴더")
    return {"id": fid}


@router.get("/{folder_id}")
def get_folder(folder_id: int, request: Request) -> dict:
    f = folder_repo.get_folder(request.app.state.deps.db, folder_id)
    if f is None:
        raise HTTPException(status_code=404, detail="folder not found")
    return f


class ItemsBody(BaseModel):
    content_ids: list[str]


@router.post("/{folder_id}/items")
def add_items(folder_id: int, body: ItemsBody, request: Request) -> dict:
    folder_repo.add_items(request.app.state.deps.db, folder_id, body.content_ids)
    return {"ok": True}


@router.delete("/{folder_id}/items/{content_id}")
def remove_item(folder_id: int, content_id: str, request: Request) -> dict:
    folder_repo.remove_item(request.app.state.deps.db, folder_id, content_id)
    return {"ok": True}


@router.delete("/{folder_id}")
def delete_folder(folder_id: int, request: Request, delete_media: bool = False) -> dict:
    """폴더 삭제. delete_media=true 면 담긴 미디어 파일까지 제거."""
    deps = request.app.state.deps
    if delete_media:
        for cid in folder_repo.content_ids(deps.db, folder_id):
            remove_media_fully(deps, cid)
        request.app.state.hub.publish(deps.player.get_state())
    folder_repo.delete_folder(deps.db, folder_id)
    return {"ok": True}
