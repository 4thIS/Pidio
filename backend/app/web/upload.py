# backend/app/web/upload.py
"""청크 업로드 (Task 7.2).

흐름: POST /api/upload/init → PUT /api/upload/{id}/chunk?index=N (×N) → POST /api/upload/{id}/complete.
complete: 청크 병합 → content_id 계산 → USB 타입 폴더로 이동 → media upsert → 백그라운드 probe/thumbnail.
대상 USB 타입 폴더가 없으면(미마운트) 409.

content_id 계산은 domain.identity, media 등록은 domain.media_repo(실 DB)로 위임(Phase 8).
"""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from app.domain import media_repo
from app.domain.identity import compute_content_id
from app.web import media_tools
from app.web.auth import require_session

router = APIRouter(
    prefix="/api/upload",
    tags=["upload"],
    dependencies=[Depends(require_session)],
)

# 미디어 타입 → USB 하위 폴더 (스캐너와 동일 규약).
_TYPE_DIR = {"video": "videos", "photo": "pictures", "music": "music"}

# 허용 확장자(통상적으로 자주 쓰이는 것만) — 그 외 파일은 업로드 거부.
_ALLOWED_EXT = {
    "video": {".mp4", ".mkv", ".mov", ".avi", ".m4v", ".webm"},
    "photo": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"},
    "music": {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg"},
}


def _unique_name(conn, name: str) -> str:
    """표시 이름이 이미 있으면 'name (1)', 'name (2)' … 로 유일하게 만든다."""
    base, ext = os.path.splitext(name)

    def taken(n: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM media WHERE original_name=? OR custom_title=? LIMIT 1", (n, n)
        ).fetchone() is not None

    if not taken(name):
        return name
    i = 1
    while True:
        cand = f"{base} ({i}){ext}"
        if not taken(cand):
            return cand
        i += 1


class InitBody(BaseModel):
    filename: str
    size: int
    type: str


@router.post("/init")
def init(body: InitBody, request: Request) -> dict:
    if body.type not in _TYPE_DIR:
        raise HTTPException(status_code=422, detail="unknown media type")
    ext = os.path.splitext(body.filename)[1].lower()
    if ext not in _ALLOWED_EXT[body.type]:
        raise HTTPException(status_code=422, detail="지원하지 않는 파일 형식")
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

    content_id = compute_content_id(str(merged))
    ext = os.path.splitext(sess["filename"])[1]
    final = type_dir / f"{content_id}{ext}"
    shutil.move(str(merged), str(final))
    rel_path = f"{_TYPE_DIR[sess['media_type']]}/{final.name}"
    # 새 파일이면 표시 이름을 유일하게(같은 이름 다른 파일 → "이름 (1)"). 같은 내용이면 dedup 유지.
    existing = media_repo.get_media(deps.db, content_id)
    display_name = sess["filename"] if existing else _unique_name(deps.db, sess["filename"])
    media_repo.upsert_media(deps.db, content_id, sess["media_type"], display_name, rel_path)

    background.add_task(
        _postprocess, deps, content_id, sess["media_type"], sess["filename"], rel_path, str(final)
    )

    shutil.rmtree(tmp_dir, ignore_errors=True)
    deps.uploads.pop(upload_id, None)
    return {"content_id": content_id}


def _postprocess(deps, content_id, media_type, filename, rel_path, path) -> None:
    """백그라운드: 길이 probe + 썸네일 생성(best-effort; 실패해도 무시)."""
    duration = media_tools.probe_duration(path)
    if duration is not None:
        # upsert 는 duration 을 COALESCE 로 갱신한다(같은 rel_path 유지).
        media_repo.upsert_media(deps.db, content_id, media_type, filename, rel_path, duration=duration)
    # 썸네일은 스키마 규약 경로 .pidio/thumbs/<cid>.jpg 에 저장(스트리밍 라우터가 같은 경로 조회).
    thumb_dir = Path(deps.media_root) / ".pidio" / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    media_tools.make_thumbnail(path, str(thumb_dir / f"{content_id}.jpg"))
