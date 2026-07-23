"""플레이리스트/예약 리포지토리 + 즉석 선택→블록 변환 (Phase 5.2).

- 플레이리스트 = 블록(동영상/슬라이드쇼)의 순서 있는 모음.
- blocks_of(): 도메인 Block 목록으로 로드(재생엔진용).
- get_playlist(): 직렬화된 dict(웹/프론트용).
- set_schedule(): 같은 타입 예약 겹침 시 ScheduleConflict.
"""
import datetime as dt

from . import media_repo, scheduler
from .contracts import Block


class ScheduleConflict(Exception):
    """같은 타입 예약이 시간상 겹칠 때."""


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


# ---- 즉석 선택 → 블록 ----

def selection_to_blocks(conn, content_ids) -> list[Block]:
    blocks: list[Block] = []
    for cid in content_ids:
        m = media_repo.get_media(conn, cid)
        if not m:
            continue
        if m["media_type"] == "video":
            blocks.append(Block(kind="video", video_id=cid))
        elif m["media_type"] == "photo":
            sec = m["default_photo_sec"] or 5.0
            blocks.append(Block(kind="slideshow", music_id=None, photos=[(cid, float(sec))]))
        else:  # music
            blocks.append(Block(kind="slideshow", music_id=cid, photos=[]))
    return blocks


# ---- 플레이리스트 CRUD ----

def create_playlist(conn, name) -> int:
    cur = conn.execute(
        "INSERT INTO playlists(name, repeat_mode, shuffle, created_at, updated_at) "
        "VALUES(?, 'off', 0, ?, ?)",
        (name, _now(), _now()),
    )
    conn.commit()
    return cur.lastrowid


def update_playlist(conn, playlist_id, name, repeat_mode, shuffle, blocks) -> None:
    conn.execute(
        "UPDATE playlists SET name=?, repeat_mode=?, shuffle=?, updated_at=? WHERE id=?",
        (name, repeat_mode, int(shuffle), _now(), playlist_id),
    )
    # 기존 블록 삭제(FK 캐스케이드로 block_photos도 정리)
    conn.execute("DELETE FROM playlist_blocks WHERE playlist_id=?", (playlist_id,))
    for pos, b in enumerate(blocks):
        cur = conn.execute(
            "INSERT INTO playlist_blocks(playlist_id, position, kind, video_id, music_id) "
            "VALUES(?,?,?,?,?)",
            (playlist_id, pos, b["kind"], b.get("video_id"), b.get("music_id")),
        )
        if b["kind"] == "slideshow":
            block_id = cur.lastrowid
            for ppos, ph in enumerate(b.get("photos", [])):
                conn.execute(
                    "INSERT INTO block_photos(block_id, position, photo_id, duration_sec) "
                    "VALUES(?,?,?,?)",
                    (block_id, ppos, ph["photo_id"], ph.get("duration_sec")),
                )
    conn.commit()


def delete_playlist(conn, playlist_id) -> None:
    conn.execute("DELETE FROM playlists WHERE id=?", (playlist_id,))
    conn.commit()


def get_playlist(conn, playlist_id):
    r = conn.execute("SELECT * FROM playlists WHERE id=?", (playlist_id,)).fetchone()
    if not r:
        return None
    return {
        "id": r["id"],
        "name": r["name"],
        "repeat_mode": r["repeat_mode"],
        "shuffle": r["shuffle"],
        "blocks": _serialize_blocks(conn, playlist_id),
        "schedule": schedule_of(conn, playlist_id),
    }


def list_playlists(conn):
    out = []
    for pl in conn.execute("SELECT * FROM playlists ORDER BY id").fetchall():
        blocks = blocks_of(conn, pl["id"])
        total = 0.0
        covers = []
        for b in blocks:
            if b.kind == "video":
                m = media_repo.get_media(conn, b.video_id)
                total += (m["duration"] or 0) if m else 0
                if b.video_id:
                    covers.append(b.video_id)
            else:
                total += sum(sec for _pid, sec in b.photos)
                covers += [pid for pid, _ in b.photos]
        out.append({
            "id": pl["id"],
            "name": pl["name"],
            "repeat_mode": pl["repeat_mode"],
            "shuffle": pl["shuffle"],
            "item_count": len(blocks),
            "total_sec": total,
            "cover_content_ids": covers[:4],
            "schedule": schedule_of(conn, pl["id"]),
        })
    return out


# ---- 블록 로드(도메인/직렬화) ----

def _photo_sec(conn, photo_id, duration_sec):
    if duration_sec is not None:
        return float(duration_sec)
    m = media_repo.get_media(conn, photo_id)
    return float(m["default_photo_sec"]) if m and m["default_photo_sec"] else 5.0


def blocks_of(conn, playlist_id) -> list[Block]:
    rows = conn.execute(
        "SELECT * FROM playlist_blocks WHERE playlist_id=? ORDER BY position",
        (playlist_id,),
    ).fetchall()
    blocks: list[Block] = []
    for r in rows:
        if r["kind"] == "video":
            blocks.append(Block(kind="video", video_id=r["video_id"]))
        else:
            prows = conn.execute(
                "SELECT photo_id, duration_sec FROM block_photos "
                "WHERE block_id=? ORDER BY position",
                (r["id"],),
            ).fetchall()
            photos = [(p["photo_id"], _photo_sec(conn, p["photo_id"], p["duration_sec"]))
                      for p in prows]
            blocks.append(Block(kind="slideshow", music_id=r["music_id"], photos=photos))
    return blocks


def _serialize_blocks(conn, playlist_id):
    rows = conn.execute(
        "SELECT * FROM playlist_blocks WHERE playlist_id=? ORDER BY position",
        (playlist_id,),
    ).fetchall()
    out = []
    for r in rows:
        if r["kind"] == "video":
            out.append({"kind": "video", "video_id": r["video_id"]})
        else:
            prows = conn.execute(
                "SELECT photo_id, duration_sec FROM block_photos "
                "WHERE block_id=? ORDER BY position",
                (r["id"],),
            ).fetchall()
            out.append({
                "kind": "slideshow",
                "music_id": r["music_id"],
                "photos": [
                    {"photo_id": p["photo_id"], "duration_sec": p["duration_sec"]}
                    for p in prows
                ],
            })
    return out


# ---- 예약 ----

def schedule_of(conn, playlist_id):
    r = conn.execute(
        "SELECT * FROM schedules WHERE playlist_id=?", (playlist_id,)
    ).fetchone()
    return dict(r) if r else None


def list_schedules(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM schedules").fetchall()]


def set_schedule(conn, playlist_id, sched) -> None:
    others = [s for s in list_schedules(conn) if s["playlist_id"] != playlist_id]
    if scheduler.overlaps_same_type(others, sched):
        raise ScheduleConflict("같은 타입의 예약과 시간이 겹칩니다")
    conn.execute("DELETE FROM schedules WHERE playlist_id=?", (playlist_id,))
    conn.execute(
        "INSERT INTO schedules(playlist_id, sched_type, start_dt, end_dt, "
        "weekdays, start_time, end_time, enabled) VALUES(?,?,?,?,?,?,?,1)",
        (
            playlist_id,
            sched["sched_type"],
            sched.get("start_dt"),
            sched.get("end_dt"),
            sched.get("weekdays"),
            sched.get("start_time"),
            sched.get("end_time"),
        ),
    )
    conn.commit()


def delete_schedule(conn, playlist_id) -> None:
    conn.execute("DELETE FROM schedules WHERE playlist_id=?", (playlist_id,))
    conn.commit()
