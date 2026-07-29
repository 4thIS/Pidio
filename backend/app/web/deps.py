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
from app.domain import media_repo
from app.domain.player import Player
from app.domain.service import AppService
from app.web.mpv_null import NullMpv

# backend/ 를 기준으로 한 기본 DB 경로.
_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "pidio.db"


def _make_mpv_clients(testing: bool):
    """PIDIO_MPV=ipc 면 실제 mpv 2인스턴스에 소켓 연결, 아니면 NullMpv.

    소켓 연결 실패(예: mpv 아직 미기동)해도 서버는 뜨고 재생만 무시된다
    (mpv 먼저 띄우고 서버 재시작하면 연결됨). 재연결 자동화는 Phase 10.2.
    """
    if testing or os.environ.get("PIDIO_MPV") != "ipc":
        return NullMpv(), NullMpv()
    from app.domain.mpv_ipc import MpvIpc

    video = MpvIpc(os.environ.get("PIDIO_MPV_VIDEO_SOCK", "/tmp/pidio/mpv-video.sock"))
    music = MpvIpc(os.environ.get("PIDIO_MPV_MUSIC_SOCK", "/tmp/pidio/mpv-music.sock"))
    for c in (video, music):
        try:
            c.connect()
        except OSError as e:  # noqa: PERF203
            print(f"[pidio] mpv 소켓 연결 실패({c.sock_path}): {e} "
                  f"— mpv 먼저 실행 후 서버 재시작 필요")
    return video, music


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

        # ---- 도메인 (Phase 8/10) ------------------------------------------
        # PIDIO_MPV=ipc 면 실제 mpv(Pi), 아니면 NullMpv(개발/테스트).
        video_mpv, music_mpv = _make_mpv_clients(self.testing)

        def _resolve_media(content_id: str) -> str:
            # content_id → USB 내 실제 절대경로(media_root + rel_path). 못 찾으면 원본.
            m = media_repo.get_media(self.db, content_id)
            if m and m["rel_path"]:
                return os.path.join(self.media_root, m["rel_path"])
            return content_id

        def _resolve_title(content_id: str) -> str:
            # content_id → 표시 제목(custom_title 우선, 없으면 원본 파일명).
            m = media_repo.get_media(self.db, content_id)
            if m:
                return m["custom_title"] or m["original_name"]
            return content_id

        self.player = Player(
            video_mpv, music_mpv,
            standby_image=os.environ.get("PIDIO_STANDBY_IMAGE", "standby.png"),
            music_screen_image=os.environ.get("PIDIO_MUSIC_IMAGE", "music.png"),
            resolve_path=_resolve_media,
            resolve_title=_resolve_title,
        )
        self.service = AppService(self.db, self.player)

    def close(self) -> None:
        self.db.close()
