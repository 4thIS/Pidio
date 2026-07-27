import datetime as dt

from app.domain import media_repo as mr
from app.domain import playlist_repo as pr
from app.domain.db import connect, init_db
from app.domain.player import Player
from app.domain.service import AppService
from tests.fakes import FakeMpv


def _svc(tmp):
    c = connect(str(tmp / "t.sqlite3"))
    init_db(c)
    v, m = FakeMpv(), FakeMpv()
    player = Player(v, m, "/standby.png", "/music.png")
    svc = AppService(c, player)
    return svc, c, player, v, m


def _make_playlist(c, name, cid="v1", repeat="off"):
    mr.upsert_media(c, cid, "video", "a.mp4", "videos/a.mp4", duration=10)
    pid = pr.create_playlist(c, name)
    pr.update_playlist(c, pid, name=name, repeat_mode=repeat, shuffle=0,
                       blocks=[{"kind": "video", "video_id": cid}])
    return pid


def test_save_queue_as_playlist(tmp_path):
    from app.domain.contracts import Block
    svc, c, player, v, m = _svc(tmp_path)
    mr.upsert_media(c, "v1", "video", "a.mp4", "videos/a.mp4", duration=10)
    mr.upsert_media(c, "p1", "photo", "1.jpg", "pictures/1.jpg")
    player.play_blocks(
        [Block(kind="video", video_id="v1"),
         Block(kind="slideshow", music_id=None, photos=[("p1", 4.0)])],
        "전체 선택",
    )
    pid = svc.save_queue_as_playlist("내 목록")
    pl = pr.get_playlist(c, pid)
    assert pl["name"] == "내 목록"
    assert pl["blocks"][0] == {"kind": "video", "video_id": "v1"}
    assert pl["blocks"][1]["kind"] == "slideshow"
    assert pl["blocks"][1]["photos"][0]["photo_id"] == "p1"


def test_play_playlist_loads_blocks_with_meta(tmp_path):
    svc, c, player, v, m = _svc(tmp_path)
    pid = _make_playlist(c, "행사", repeat="all")
    svc.play_playlist(pid)
    assert v.loaded == "v1"
    assert player.source_label == "행사"
    assert player.repeat == "all"


def test_play_selection_is_manual(tmp_path):
    svc, c, player, v, m = _svc(tmp_path)
    mr.upsert_media(c, "v1", "video", "a.mp4", "videos/a.mp4")
    svc.play_selection(["v1"])
    assert v.loaded == "v1"
    assert player.mode == "manual"


def test_evaluate_standby_when_no_active_no_default(tmp_path):
    svc, c, player, v, m = _svc(tmp_path)
    player.mode = "auto"
    svc.evaluate_schedule(dt.datetime(2026, 9, 1, 10, 0))
    assert v.loaded == "/standby.png"


def test_evaluate_ignored_in_manual_mode(tmp_path):
    svc, c, player, v, m = _svc(tmp_path)
    mr.upsert_media(c, "v1", "video", "a.mp4", "videos/a.mp4")
    svc.play_selection(["v1"])                      # manual
    svc.evaluate_schedule(dt.datetime(2026, 9, 1, 10, 0))
    assert v.loaded == "v1"                         # 안 바뀜(수동 우선)


def test_evaluate_switches_to_scheduled_playlist(tmp_path):
    svc, c, player, v, m = _svc(tmp_path)
    pid = _make_playlist(c, "점심")
    pr.set_schedule(c, pid, {"sched_type": "weekly", "weekdays": "mon",
                             "start_time": "12:00", "end_time": "13:00"})
    player.mode = "auto"
    svc.evaluate_schedule(dt.datetime(2026, 8, 3, 12, 30))   # 월 12:30
    assert v.loaded == "v1"
    assert player.source_label == "점심"


def test_resume_auto_applies_default_playlist(tmp_path):
    svc, c, player, v, m = _svc(tmp_path)
    pid = _make_playlist(c, "기본")
    c.execute("INSERT INTO settings(key,value) VALUES('default_playlist_id',?)", (str(pid),))
    c.commit()
    svc.play_selection(["v1"])                      # 수동 오버라이드
    assert player.mode == "manual"
    svc.resume_auto()                               # 자동 복귀 → 기본 재생목록
    assert player.mode == "auto"
    assert player.source_label == "기본"


def test_scheduled_end_returns_to_standby(tmp_path):
    svc, c, player, v, m = _svc(tmp_path)
    pid = _make_playlist(c, "점심")
    pr.set_schedule(c, pid, {"sched_type": "weekly", "weekdays": "mon",
                             "start_time": "12:00", "end_time": "13:00"})
    player.mode = "auto"
    svc.evaluate_schedule(dt.datetime(2026, 8, 3, 12, 30))   # 활성
    assert v.loaded == "v1"
    svc.evaluate_schedule(dt.datetime(2026, 8, 3, 13, 30))   # 종료 후 → 대기
    assert v.loaded == "/standby.png"


def test_source_playlist_id_tracked(tmp_path):
    svc, c, player, v, m = _svc(tmp_path)
    pid = _make_playlist(c, "행사")
    svc.play_playlist(pid)
    assert svc.current_source_playlist_id == pid
    svc.play_selection(["v1"])
    assert svc.current_source_playlist_id is None
