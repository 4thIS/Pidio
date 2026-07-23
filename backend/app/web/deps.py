# backend/app/web/deps.py
"""웹 계층 의존성: 도메인(DB·Player·AppService) 조립 (Phase 8 통합).

테스트 모드에서는 in-memory SQLite 로 격리한다.
Player 의 mpv 는 개발/비-Pi 에서 NullMpv, Pi(Phase 10)에서 MpvIpc 로 교체된다.
"""
from __future__ import annotations
import os
import tempfile
from pathlib import Path

from app.domain import db as domain_db
from app.domain.player import Player
from app.domain.service import AppService
from app.web.mpv_null import NullMpv

# backend/ 를 기준으로 한 기본 DB 경로.
_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "pidio.db"


class Deps:
    """요청 간 공유되는 싱글턴 컨테이너."""

    def __init__(self, testing: bool = False) -> None:
        self.testing = testing
        db_target = ":memory:" if testing else os.environ.get("PIDIO_DB", str(_DEFAULT_DB))
        # 도메인 스키마로 초기화된 연결(설정 테이블 포함). auth 도 이 settings 테이블을 공유.
        self.db = domain_db.connect(db_target)
        domain_db.init_db(self.db)

        # 공용 비번에 대한 연속 로그인 실패 카운터(간단 rate limit).
        self.login_fails = 0

        # ---- 업로드/미디어 (Phase 7) --------------------------------------
        # USB 미디어 루트. 이 경로(타입 폴더)가 없으면 "미마운트"로 간주(409).
        self.media_root = os.environ.get("PIDIO_MEDIA_ROOT", "/media/usb")
        # 청크 임시 저장 위치.
        self.upload_tmp = os.environ.get(
            "PIDIO_UPLOAD_TMP", str(Path(tempfile.gettempdir()) / "pidio_upload")
        )
        # 진행 중인 업로드 세션: upload_id -> {filename,size,media_type,tmp_dir}.
        self.uploads: dict[str, dict] = {}

        # ---- 도메인 (Phase 8) ---------------------------------------------
        # 개발/비-Pi: NullMpv. Pi(Phase 10)에서 MpvIpc 로 교체.
        self.player = Player(
            NullMpv(), NullMpv(),
            standby_image="standby.png",
            music_screen_image="music.png",
        )
        self.service = AppService(self.db, self.player)

    def close(self) -> None:
        self.db.close()
