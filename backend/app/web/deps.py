# backend/app/web/deps.py
"""웹 계층 의존성: DB 연결·서비스 싱글턴 제공.

테스트 모드에서는 in-memory SQLite 를 사용해 격리한다.
AppService(도메인, CW 소유) 연결은 Phase 8 통합 시점에 여기서 이뤄진다.
"""
from __future__ import annotations
import os
import sqlite3
import tempfile
from pathlib import Path

from app.web.adapters import fake_content_id, FakeMediaStore

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

        # ---- 업로드/미디어 (Phase 7) --------------------------------------
        # USB 미디어 루트. 이 경로(타입 폴더)가 없으면 "미마운트"로 간주(409).
        # 운영(Pi) 기본 /media/usb, 개발/테스트는 override.
        self.media_root = os.environ.get("PIDIO_MEDIA_ROOT", "/media/usb")
        # 청크 임시 저장 위치.
        self.upload_tmp = os.environ.get(
            "PIDIO_UPLOAD_TMP", str(Path(tempfile.gettempdir()) / "pidio_upload")
        )
        # 진행 중인 업로드 세션: upload_id -> {filename,size,media_type,tmp_dir}.
        self.uploads: dict[str, dict] = {}
        # 가짜 어댑터(Phase 8 에서 CW 도메인으로 교체).
        self.compute_content_id = fake_content_id
        self.media_store = FakeMediaStore()

    def close(self) -> None:
        self.db.close()
