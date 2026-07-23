# backend/tests/test_background.py
"""E-6 백그라운드 스케줄 루프 (Task 8.6) — tick 단위 로직."""
import datetime as dt

from app.domain import media_repo, playlist_repo
from app.web.background import startup_scan, tick
from app.web.deps import Deps
from app.web.sse import StateHub


def _setup():
    deps = Deps(testing=True)
    hub = StateHub()
    db = deps.db
    media_repo.upsert_media(db, "v1", "video", "a.mp4", "videos/v1.mp4", duration=10.0)
    pid = playlist_repo.create_playlist(db, "점심")
    playlist_repo.update_playlist(db, pid, "점심", "off", False, [{"kind": "video", "video_id": "v1"}])
    playlist_repo.set_schedule(db, pid, {
        "sched_type": "weekly", "weekdays": "mon", "start_time": "12:00", "end_time": "13:00",
    })
    return deps, hub, pid


MON_1230 = dt.datetime(2026, 8, 3, 12, 30)  # 월요일


def test_tick_auto_activates_scheduled_playlist():
    deps, hub, pid = _setup()
    deps.player.resume_auto()                 # 자동 모드
    tick(deps, hub, now=MON_1230)
    st = deps.player.get_state()
    assert st.source_label == "점심" and st.queue_len == 1


def test_tick_manual_mode_no_change():
    deps, hub, pid = _setup()
    # 기본 모드는 manual → 스케줄 판정 무시
    tick(deps, hub, now=MON_1230)
    assert deps.player.get_state().source_label is None


def test_startup_scan_populates_media(tmp_path):
    deps = Deps(testing=True)
    usb = tmp_path / "usb"
    (usb / "videos").mkdir(parents=True)
    (usb / "videos" / "a.mp4").write_bytes(b"x" * 30)
    deps.media_root = str(usb)
    n = startup_scan(deps)
    assert n == 1
    assert len(media_repo.list_media(deps.db, "video")) == 1


def test_startup_scan_no_media_root_is_noop(tmp_path):
    deps = Deps(testing=True)
    deps.media_root = str(tmp_path / "nope")
    assert startup_scan(deps) == 0


def test_tick_publishes_state():
    deps, hub, pid = _setup()
    received = []

    # StateHub 에 구독자 큐를 직접 넣어 publish 수신 확인(동기).
    import asyncio
    q: asyncio.Queue = asyncio.Queue()
    hub._subscribers.add(q)
    tick(deps, hub, now=MON_1230)
    assert not q.empty()
