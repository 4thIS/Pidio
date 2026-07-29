"""폴더(수동 미디어 그룹) 리포지토리.

폴더 = 사용자가 드래그로 담는 이름 있는 미디어 묶음(동영상/사진/음악 혼합 가능).
- 태그식 소속: 한 미디어가 여러 폴더에 중복 소속 가능하고, 폴더에 담겨도
  타입 탭(전체/동영상/사진/음악)엔 계속 보인다.
- 폴더 삭제 시 미디어 파일 삭제 여부는 웹 계층이 결정(여기선 묶음만 정리).
"""
import datetime as dt

from . import media_repo


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def list_folders(conn):
    out = []
    for f in conn.execute("SELECT * FROM folders ORDER BY sort_order, id").fetchall():
        n = conn.execute(
            "SELECT COUNT(*) FROM folder_items WHERE folder_id=?", (f["id"],)
        ).fetchone()[0]
        out.append({"id": f["id"], "name": f["name"], "item_count": n})
    return out


def create_folder(conn, name) -> int:
    nxt = conn.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM folders").fetchone()[0]
    cur = conn.execute(
        "INSERT INTO folders(name, sort_order, created_at) VALUES(?,?,?)", (name, nxt, _now())
    )
    conn.commit()
    return cur.lastrowid


def reorder_folders(conn, ordered_ids) -> None:
    """드래그 재정렬: 주어진 id 순서대로 sort_order 재부여."""
    for pos, fid in enumerate(ordered_ids):
        conn.execute("UPDATE folders SET sort_order=? WHERE id=?", (pos, fid))
    conn.commit()


def delete_folder(conn, folder_id) -> None:
    conn.execute("DELETE FROM folder_items WHERE folder_id=?", (folder_id,))
    conn.execute("DELETE FROM folders WHERE id=?", (folder_id,))
    conn.commit()


def add_items(conn, folder_id, content_ids) -> None:
    for cid in content_ids:
        if media_repo.get_media(conn, cid):  # 존재하는 미디어만
            conn.execute(
                "INSERT OR IGNORE INTO folder_items(folder_id, content_id, added_at) "
                "VALUES(?,?,?)",
                (folder_id, cid, _now()),
            )
    conn.commit()


def remove_item(conn, folder_id, content_id) -> None:
    conn.execute(
        "DELETE FROM folder_items WHERE folder_id=? AND content_id=?",
        (folder_id, content_id),
    )
    conn.commit()


def content_ids(conn, folder_id) -> list[str]:
    rows = conn.execute(
        "SELECT content_id FROM folder_items WHERE folder_id=? ORDER BY added_at, content_id",
        (folder_id,),
    ).fetchall()
    return [r["content_id"] for r in rows]


def get_folder(conn, folder_id):
    f = conn.execute("SELECT * FROM folders WHERE id=?", (folder_id,)).fetchone()
    if not f:
        return None
    return {"id": f["id"], "name": f["name"], "content_ids": content_ids(conn, folder_id)}
