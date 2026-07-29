# backend/app/web/media_ops.py
"""미디어 파일 완전 삭제 헬퍼 (media 라우터·folders 라우터 공용).

USB 원본 파일 + 썸네일 언링크 → DB 행/플리블록/폴더소속 제거 → 라이브 큐 정리.
"""
from __future__ import annotations

from pathlib import Path

from app.domain import media_repo


def remove_media_fully(deps, content_id: str) -> None:
    m = media_repo.get_media(deps.db, content_id)
    if m and m["rel_path"]:
        try:
            (Path(deps.media_root) / m["rel_path"]).unlink()
        except OSError:
            pass
    try:
        (Path(deps.media_root) / ".pidio" / "thumbs" / f"{content_id}.jpg").unlink()
    except OSError:
        pass
    media_repo.delete_media(deps.db, content_id)
    deps.player.remove_content(content_id)  # 재생 중이면 큐에서도 제거
