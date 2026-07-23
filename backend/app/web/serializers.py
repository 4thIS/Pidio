# backend/app/web/serializers.py
"""도메인 DB row → 프론트 계약 형태 직렬화."""
from __future__ import annotations


def media_out(row: dict) -> dict:
    """media 행 → {content_id, media_type, title, duration, thumb_url, available}."""
    return {
        "content_id": row["content_id"],
        "media_type": row["media_type"],
        "title": row["custom_title"] or row["original_name"],
        "duration": row["duration"],
        "thumb_url": f"/thumb/{row['content_id']}" if row["media_type"] != "music" else None,
        "available": bool(row["available"]),
    }
