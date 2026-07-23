# backend/app/web/adapters.py
"""Phase 8 통합 전까지 쓰는 가짜(in-memory) 어댑터.

CW 도메인이 완성되면 deps 에서 실제 것으로 교체한다:
- fake_content_id  → domain.identity.compute_content_id
- FakeMediaStore   → domain.media_repo (sqlite)
계약(반환 필드)만 맞추고 로직은 최소로 흉내낸다.
"""
from __future__ import annotations

import hashlib
import os


def fake_content_id(path: str) -> str:
    """CW identity.compute_content_id 대체 스텁. 파일 내용 기반 안정적 식별자."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:16]
    return f"{size}-{digest}"


class FakeMediaStore:
    """in-memory 미디어 저장소. Phase 8 에서 media_repo 로 교체."""

    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}

    def upsert(self, content_id, media_type, original_name, rel_path, duration=None) -> None:
        self._rows[content_id] = {
            "content_id": content_id,
            "media_type": media_type,
            "original_name": original_name,
            "rel_path": rel_path,
            "duration": duration,
        }

    def get(self, content_id) -> dict | None:
        return self._rows.get(content_id)

    def list(self, media_type=None) -> list[dict]:
        return [
            r for r in self._rows.values()
            if media_type in (None, "all") or r["media_type"] == media_type
        ]
