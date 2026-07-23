# backend/app/web/upload.py
"""청크 업로드 (Task 7.2).

흐름: POST /api/upload/init → PUT /api/upload/{id}/chunk?index=N (×N) → POST /api/upload/{id}/complete.
complete: 청크 병합 → content_id 계산 → USB 타입 폴더로 이동 → media upsert → 백그라운드 probe/thumbnail.
대상 USB 타입 폴더가 없으면(미마운트) 409.

content_id 계산·media upsert 는 현재 가짜 어댑터(deps)를 통하며 Phase 8 에서 CW 도메인으로 교체된다.
"""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from app.web import media_tools
from app.web.auth import require_session

router = APIRouter(
    prefix="/api/upload",
    tags=["upload"],
    dependencies=[Depends(require_session)],
)

# 미디어 타입 → USB 하위 폴더 (스캐너와 동일 규약).
_TYPE_DIR = {"video": "videos", "photo": "pictures", "music": "music"}


class InitBody(BaseModel):
    filename: str
    size: int
    type: str


@router.post("/init")
def init(body: InitBody, request: Request) -> dict:
    if body.type not in _TYPE_DIR:
        raise HTTPException(status_code=422, detail="unknown media type")
    deps = request.app.state.deps
    upload_id = uuid.uuid4().hex
    tmp_dir = Path(deps.upload_tmp) / upload_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    deps.uploads[upload_id] = {
        "filename": body.filename,
        "size": body.size,
        "media_type": body.type,
        "tmp_dir": str(tmp_dir),
    }
    return {"upload_id": upload_id}


@router.put("/{upload_id}/chunk")
async def chunk(upload_id: str, index: int, request: Request) -> dict:
    deps = request.app.state.deps
    sess = deps.uploads.get(upload_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="unknown upload")
    data = await request.body()
    part = Path(sess["tmp_dir"]) / f"{index:08d}.part"
    part.write_bytes(data)
    return {"ok": True, "index": index}


@router.post("/{upload_id}/complete")
def complete(upload_id: str, request: Request, background: BackgroundTasks) -> dict:
    deps = request.app.state.deps
    sess = deps.uploads.get(upload_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="unknown upload")

    type_dir = Path(deps.media_root) / _TYPE_DIR[sess["media_type"]]
    if not type_dir.is_dir():
        raise HTTPException(status_code=409, detail="USB 미마운트")

    tmp_dir = Path(sess["tmp_dir"])
    merged = tmp_dir / "merged"
    with open(merged, "wb") as out:
        for part in sorted(tmp_dir.glob("*.part")):
            out.write(part.read_bytes())

    content_id = deps.compute_content_id(str(merged))
    ext = os.path.splitext(sess["filename"])[1]
    final = type_dir / f"{content_id}{ext}"
    shutil.move(str(merged), str(final))
    rel_path = f"{_TYPE_DIR[sess['media_type']]}/{final.name}"
    deps.media_store.upsert(content_id, sess["media_type"], sess["filename"], rel_path)

    background.add_task(_postprocess, deps, content_id, str(final))

    shutil.rmtree(tmp_dir, ignore_errors=True)
    deps.uploads.pop(upload_id, None)
    return {"content_id": content_id}


def _postprocess(deps, content_id: str, path: str) -> None:
    """백그라운드: 길이 probe + 썸네일 생성(best-effort; 실패해도 무시)."""
    duration = media_tools.probe_duration(path)
    if duration is not None:
        row = deps.media_store.get(content_id)
        if row is not None:
            row["duration"] = duration
    thumb_dir = Path(deps.media_root) / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    media_tools.make_thumbnail(path, str(thumb_dir / f"{content_id}.jpg"))
