"""미디어 메타데이터 리포지토리 (Phase 2.3).

파일 자체는 USB가 진실이고, 여기서는 content_id에 연결된 부가정보만 다룬다.
- upsert_media: 스캔 시 발견 → 있으면 갱신(available=1 복원)·없으면 삽입.
- set_available: 이번 스캔에 존재하는 집합만 available=1, 나머지 0(삭제 아님).
"""
import datetime as dt


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def upsert_media(conn, content_id, media_type, original_name, rel_path, duration=None):
    row = conn.execute(
        "SELECT content_id FROM media WHERE content_id=?", (content_id,)
    ).fetchone()
    if row:
        conn.execute(
            """UPDATE media SET rel_path=?, available=1, last_seen=?,
                   duration=COALESCE(?, duration)
               WHERE content_id=?""",
            (rel_path, _now(), duration, content_id),
        )
    else:
        conn.execute(
            """INSERT INTO media(content_id, media_type, original_name, rel_path,
                   duration, default_photo_sec, available, first_seen, last_seen)
               VALUES(?,?,?,?,?,?,1,?,?)""",
            (
                content_id,
                media_type,
                original_name,
                rel_path,
                duration,
                5.0 if media_type == "photo" else None,
                _now(),
                _now(),
            ),
        )
    conn.commit()


def set_available(conn, content_ids) -> None:
    conn.execute("UPDATE media SET available=0")
    if content_ids:
        placeholders = ",".join("?" * len(content_ids))
        conn.execute(
            f"UPDATE media SET available=1 WHERE content_id IN ({placeholders})",
            tuple(content_ids),
        )
    conn.commit()


def get_media(conn, content_id):
    r = conn.execute(
        "SELECT * FROM media WHERE content_id=?", (content_id,)
    ).fetchone()
    return dict(r) if r else None


def list_media(conn, media_type=None):
    if media_type and media_type != "all":
        rows = conn.execute(
            "SELECT * FROM media WHERE available=1 AND media_type=? "
            "ORDER BY original_name",
            (media_type,),
        )
    else:
        rows = conn.execute(
            "SELECT * FROM media WHERE available=1 ORDER BY media_type, original_name"
        )
    return [dict(r) for r in rows]


def set_custom_title(conn, content_id, title) -> None:
    conn.execute(
        "UPDATE media SET custom_title=? WHERE content_id=?", (title, content_id)
    )
    conn.commit()


def delete_media(conn, content_id) -> None:
    """미디어 DB 행 + 이를 참조하는 플리 블록/사진 제거(파일 삭제는 웹 계층)."""
    conn.execute("DELETE FROM block_photos WHERE photo_id=?", (content_id,))
    conn.execute(
        "DELETE FROM playlist_blocks WHERE video_id=? OR music_id=?",
        (content_id, content_id),
    )
    conn.execute("DELETE FROM media WHERE content_id=?", (content_id,))
    conn.commit()
