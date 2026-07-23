# backend/app/web/streaming.py
"""Range 스트리밍 & 썸네일 서빙 (Task 7.3).

- GET /stream/{content_id} : HTTP Range(206 + Content-Range) 지원 원본 스트림. Range 없으면 200 전체.
- GET /thumb/{content_id}  : jpeg 썸네일.
없는 content_id / 파일 없음 → 404.

content_id → 경로 해석은 media_repo(rel_path) + media_root 로 한다(Phase 8, 실 DB).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from app.domain import media_repo

router = APIRouter(tags=["stream"])

_CHUNK = 64 * 1024


def _resolve(deps, content_id: str) -> Path | None:
    row = media_repo.get_media(deps.db, content_id)
    if row is None or not row.get("rel_path"):
        return None
    path = Path(deps.media_root) / row["rel_path"]
    return path if path.is_file() else None


def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
    """'bytes=start-end' → (start, end) 포함 범위. 누락값은 각각 0 / 마지막바이트."""
    _, _, rng = range_header.partition("=")
    start_s, _, end_s = rng.partition("-")
    start = int(start_s) if start_s else 0
    end = int(end_s) if end_s else file_size - 1
    end = min(end, file_size - 1)
    return start, end


@router.get("/stream/{content_id}")
def stream(content_id: str, request: Request):
    deps = request.app.state.deps
    path = _resolve(deps, content_id)
    if path is None:
        raise HTTPException(status_code=404, detail="not found")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    if range_header is None:
        return FileResponse(str(path), headers={"Accept-Ranges": "bytes"})

    start, end = _parse_range(range_header, file_size)
    length = end - start + 1

    def body() -> Iterator[bytes]:
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(_CHUNK, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
    }
    return StreamingResponse(
        body(), status_code=206, headers=headers, media_type="application/octet-stream"
    )


@router.get("/thumb/{content_id}")
def thumb(content_id: str, request: Request):
    deps = request.app.state.deps
    if media_repo.get_media(deps.db, content_id) is None:
        raise HTTPException(status_code=404, detail="not found")
    thumb_path = Path(deps.media_root) / ".pidio" / "thumbs" / f"{content_id}.jpg"
    if not thumb_path.is_file():
        raise HTTPException(status_code=404, detail="no thumbnail")
    return FileResponse(str(thumb_path), media_type="image/jpeg")
