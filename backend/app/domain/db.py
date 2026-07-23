"""SQLite 연결·초기화 헬퍼 (Phase 2.2).

- connect(): Row factory + 외래키(FK) 활성화된 연결 반환.
- init_db(): schema.sql 실행(재실행 안전).
ORM 미사용 — 표준 sqlite3만 사용.
"""
import pathlib
import sqlite3

_SCHEMA = pathlib.Path(__file__).parent / "schema.sql"


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    conn.commit()
