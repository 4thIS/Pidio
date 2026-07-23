from app.domain.db import connect, init_db


def _fresh(tmp_path):
    conn = connect(str(tmp_path / "t.sqlite3"))
    init_db(conn)
    return conn


def test_init_creates_all_tables(tmp_path):
    conn = _fresh(tmp_path)
    names = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {
        "media",
        "playlists",
        "playlist_blocks",
        "block_photos",
        "schedules",
        "settings",
    } <= names


def test_foreign_keys_enabled(tmp_path):
    conn = _fresh(tmp_path)
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_row_factory_allows_name_access(tmp_path):
    conn = _fresh(tmp_path)
    conn.execute("INSERT INTO settings(key, value) VALUES('k','v')")
    row = conn.execute("SELECT key, value FROM settings").fetchone()
    assert row["key"] == "k" and row["value"] == "v"


def test_init_db_is_idempotent(tmp_path):
    # 이미 초기화된 DB에 init_db 재실행해도 예외 없어야 함(앱 재시작 대비)
    conn = _fresh(tmp_path)
    init_db(conn)  # 두 번째 호출
    names = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "media" in names
