# backend/app/web/deps.py
"""웹 계층 의존성: DB 연결·서비스 싱글턴 제공.

테스트 모드에서는 in-memory SQLite 를 사용해 격리한다.
AppService(도메인, CW 소유) 연결은 Phase 8 통합 시점에 여기서 이뤄진다.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path

# backend/ 를 기준으로 한 기본 DB 경로 (Phase 6 단계에선 아직 스키마 미사용).
_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "pidio.db"


class Deps:
    """요청 간 공유되는 싱글턴 컨테이너."""

    def __init__(self, testing: bool = False) -> None:
        self.testing = testing
        db_target = ":memory:" if testing else str(_DEFAULT_DB)
        # check_same_thread=False: FastAPI 의 스레드풀에서 접근 허용.
        self.db = sqlite3.connect(db_target, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )
        self.db.commit()
        # 공용 비번에 대한 연속 로그인 실패 카운터(간단 rate limit).
        self.login_fails = 0

    def close(self) -> None:
        self.db.close()
