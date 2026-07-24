import pytest

from app.domain import media_repo as mr
from app.domain import playlist_repo as pr
from app.domain.db import connect, init_db


def _c(tmp):
    c = connect(str(tmp / "t.sqlite3"))
    init_db(c)
    return c


def _seed_media(c):
    mr.upsert_media(c, "v1", "video", "a.mp4", "videos/a.mp4", duration=10)
    mr.upsert_media(c, "p1", "photo", "1.jpg", "pictures/1.jpg")
    mr.upsert_media(c, "p2", "photo", "2.jpg", "pictures/2.jpg")
    mr.upsert_media(c, "m1", "music", "s.mp3", "music/s.mp3", duration=200)


# ---- selection_to_blocks (즉석 선택) ----

def test_selection_to_blocks_by_type(tmp_path):
    c = _c(tmp_path)
    _seed_media(c)
    blocks = pr.selection_to_blocks(c, ["v1", "p1", "m1"])
    assert blocks[0].kind == "video" and blocks[0].video_id == "v1"
    # 사진 → 무음 슬라이드쇼(기본 표시시간)
    assert blocks[1].kind == "slideshow" and blocks[1].music_id is None
    assert blocks[1].photos == [("p1", 5.0)]
    # 음악 → 사진 없는 슬라이드쇼(음악 정보화면)
    assert blocks[2].kind == "slideshow" and blocks[2].music_id == "m1"
    assert blocks[2].photos == []


# ---- 플레이리스트 CRUD + 블록 왕복 ----

def test_create_and_get_empty(tmp_path):
    c = _c(tmp_path)
    pid = pr.create_playlist(c, "빈목록")
    pl = pr.get_playlist(c, pid)
    assert pl["name"] == "빈목록" and pl["blocks"] == []
    assert pl["repeat_mode"] == "off" and pl["shuffle"] == 0


def test_save_and_load_blocks_roundtrip(tmp_path):
    c = _c(tmp_path)
    _seed_media(c)
    pid = pr.create_playlist(c, "행사")
    pr.update_playlist(
        c, pid, name="행사", repeat_mode="all", shuffle=1,
        blocks=[
            {"kind": "video", "video_id": "v1"},
            {"kind": "slideshow", "music_id": "m1",
             "photos": [{"photo_id": "p1", "duration_sec": 7},
                        {"photo_id": "p2", "duration_sec": None}]},
        ],
    )
    # 도메인 Block 으로 로드
    blocks = pr.blocks_of(c, pid)
    assert blocks[0].kind == "video" and blocks[0].video_id == "v1"
    assert blocks[1].kind == "slideshow" and blocks[1].music_id == "m1"
    # duration_sec None 은 media.default_photo_sec(5) 로 대체
    assert blocks[1].photos == [("p1", 7.0), ("p2", 5.0)]


def test_get_playlist_serialized_and_meta(tmp_path):
    c = _c(tmp_path)
    _seed_media(c)
    pid = pr.create_playlist(c, "x")
    pr.update_playlist(c, pid, name="x", repeat_mode="one", shuffle=0,
                       blocks=[{"kind": "video", "video_id": "v1"}])
    pl = pr.get_playlist(c, pid)
    assert pl["repeat_mode"] == "one"
    assert pl["blocks"][0]["kind"] == "video"
    assert pl["blocks"][0]["video_id"] == "v1"


def test_update_replaces_blocks(tmp_path):
    c = _c(tmp_path)
    _seed_media(c)
    pid = pr.create_playlist(c, "x")
    pr.update_playlist(c, pid, name="x", repeat_mode="off", shuffle=0,
                       blocks=[{"kind": "video", "video_id": "v1"}])
    pr.update_playlist(c, pid, name="x", repeat_mode="off", shuffle=0,
                       blocks=[{"kind": "slideshow", "music_id": None,
                                "photos": [{"photo_id": "p1", "duration_sec": 3}]}])
    blocks = pr.blocks_of(c, pid)
    assert len(blocks) == 1 and blocks[0].kind == "slideshow"


def test_list_playlists_counts(tmp_path):
    c = _c(tmp_path)
    _seed_media(c)
    pid = pr.create_playlist(c, "행사")
    pr.update_playlist(c, pid, name="행사", repeat_mode="off", shuffle=0,
                       blocks=[{"kind": "video", "video_id": "v1"},
                               {"kind": "slideshow", "music_id": "m1", "photos": []}])
    pls = pr.list_playlists(c)
    assert len(pls) == 1 and pls[0]["item_count"] == 2


def test_delete_playlist_cascades(tmp_path):
    c = _c(tmp_path)
    _seed_media(c)
    pid = pr.create_playlist(c, "x")
    pr.update_playlist(c, pid, name="x", repeat_mode="off", shuffle=0,
                       blocks=[{"kind": "slideshow", "music_id": None,
                                "photos": [{"photo_id": "p1", "duration_sec": 3}]}])
    pr.delete_playlist(c, pid)
    assert pr.get_playlist(c, pid) is None
    # 블록/사진도 캐스케이드 삭제
    assert c.execute("SELECT COUNT(*) FROM playlist_blocks").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM block_photos").fetchone()[0] == 0


# ---- 예약 ----

def test_set_and_list_schedule(tmp_path):
    c = _c(tmp_path)
    pid = pr.create_playlist(c, "점심")
    pr.set_schedule(c, pid, {"sched_type": "weekly", "weekdays": "mon,tue",
                             "start_time": "12:00", "end_time": "13:00"})
    scheds = pr.list_schedules(c)
    assert len(scheds) == 1 and scheds[0]["playlist_id"] == pid


def test_schedule_overlap_same_type_rejected(tmp_path):
    c = _c(tmp_path)
    p1 = pr.create_playlist(c, "점심")
    pr.set_schedule(c, p1, {"sched_type": "weekly", "weekdays": "mon",
                            "start_time": "12:00", "end_time": "13:00"})
    p2 = pr.create_playlist(c, "점심2")
    with pytest.raises(pr.ScheduleConflict):
        pr.set_schedule(c, p2, {"sched_type": "weekly", "weekdays": "mon",
                                "start_time": "12:30", "end_time": "13:30"})


def test_schedule_overlap_different_type_ok(tmp_path):
    c = _c(tmp_path)
    p1 = pr.create_playlist(c, "시험")
    pr.set_schedule(c, p1, {"sched_type": "date_range",
                            "start_dt": "2026-08-01 00:00", "end_dt": "2026-08-07 00:00"})
    p2 = pr.create_playlist(c, "점심")
    # 다른 타입은 겹쳐도 OK
    pr.set_schedule(c, p2, {"sched_type": "weekly", "weekdays": "mon",
                            "start_time": "12:00", "end_time": "13:00"})
    assert len(pr.list_schedules(c)) == 2


def test_set_schedule_replaces_own_without_conflict(tmp_path):
    c = _c(tmp_path)
    pid = pr.create_playlist(c, "점심")
    pr.set_schedule(c, pid, {"sched_type": "weekly", "weekdays": "mon",
                             "start_time": "12:00", "end_time": "13:00"})
    # 같은 플리의 예약을 갱신 → 자기 자신과는 충돌 아님
    pr.set_schedule(c, pid, {"sched_type": "weekly", "weekdays": "mon",
                             "start_time": "12:10", "end_time": "13:10"})
    scheds = pr.list_schedules(c)
    assert len(scheds) == 1 and scheds[0]["start_time"] == "12:10"


def test_delete_schedule(tmp_path):
    c = _c(tmp_path)
    pid = pr.create_playlist(c, "점심")
    pr.set_schedule(c, pid, {"sched_type": "weekly", "weekdays": "mon",
                             "start_time": "12:00", "end_time": "13:00"})
    pr.delete_schedule(c, pid)
    assert pr.list_schedules(c) == []


def test_append_selection_keeps_existing(tmp_path):
    c = _c(tmp_path)
    _seed_media(c)
    pid = pr.create_playlist(c, "행사")
    pr.update_playlist(c, pid, name="행사", repeat_mode="off", shuffle=0,
                       blocks=[{"kind": "video", "video_id": "v1"}])
    pr.append_selection(c, pid, ["p1", "m1"])   # 사진·음악 추가
    blocks = pr.blocks_of(c, pid)
    assert len(blocks) == 3
    assert blocks[0].kind == "video"
    assert blocks[1].kind == "slideshow" and blocks[1].photos  # 사진
    assert blocks[2].kind == "slideshow" and blocks[2].music_id == "m1"
