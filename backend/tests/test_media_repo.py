from app.domain import media_repo as mr
from app.domain.db import connect, init_db


def _conn(tmp_path):
    c = connect(str(tmp_path / "t.sqlite3"))
    init_db(c)
    return c


def test_upsert_and_get(tmp_path):
    c = _conn(tmp_path)
    mr.upsert_media(c, "id1", "video", "a.mp4", "videos/a.mp4", duration=12.0)
    m = mr.get_media(c, "id1")
    assert m["media_type"] == "video"
    assert m["available"] == 1
    assert m["duration"] == 12.0


def test_get_missing_returns_none(tmp_path):
    c = _conn(tmp_path)
    assert mr.get_media(c, "nope") is None


def test_photo_gets_default_photo_sec(tmp_path):
    c = _conn(tmp_path)
    mr.upsert_media(c, "p1", "photo", "b.jpg", "pictures/b.jpg")
    assert mr.get_media(c, "p1")["default_photo_sec"] == 5.0


def test_set_available_marks_missing_zero(tmp_path):
    c = _conn(tmp_path)
    mr.upsert_media(c, "id1", "video", "a.mp4", "videos/a.mp4")
    mr.upsert_media(c, "id2", "photo", "b.jpg", "pictures/b.jpg")
    mr.set_available(c, {"id1"})  # id2 는 스캔에서 사라짐
    assert mr.get_media(c, "id1")["available"] == 1
    assert mr.get_media(c, "id2")["available"] == 0


def test_custom_title_overrides(tmp_path):
    c = _conn(tmp_path)
    mr.upsert_media(c, "id1", "video", "a.mp4", "videos/a.mp4")
    mr.set_custom_title(c, "id1", "졸업영상")
    assert mr.get_media(c, "id1")["custom_title"] == "졸업영상"


def test_upsert_updates_relpath_keeps_title_and_restores_available(tmp_path):
    c = _conn(tmp_path)
    mr.upsert_media(c, "id1", "video", "a.mp4", "videos/a.mp4")
    mr.set_custom_title(c, "id1", "제목")
    mr.set_available(c, set())  # 사라짐 -> available=0
    mr.upsert_media(c, "id1", "video", "a.mp4", "videos/sub/a.mp4")  # 이동 후 재발견
    m = mr.get_media(c, "id1")
    assert m["rel_path"] == "videos/sub/a.mp4"
    assert m["custom_title"] == "제목"      # 사용자 메타 보존
    assert m["available"] == 1              # 재발견 -> 복원


def test_list_media_filters_available_and_type(tmp_path):
    c = _conn(tmp_path)
    mr.upsert_media(c, "v1", "video", "a.mp4", "videos/a.mp4")
    mr.upsert_media(c, "p1", "photo", "b.jpg", "pictures/b.jpg")
    mr.upsert_media(c, "gone", "video", "c.mp4", "videos/c.mp4")
    mr.set_available(c, {"v1", "p1"})  # gone 은 available=0
    vids = mr.list_media(c, "video")
    ids = {m["content_id"] for m in vids}
    assert ids == {"v1"}  # gone 제외, photo 제외
    allm = mr.list_media(c, None)
    assert {m["content_id"] for m in allm} == {"v1", "p1"}


def test_delete_media_removes_row_and_refs(tmp_path):
    from app.domain import playlist_repo as pr
    c = _conn(tmp_path)
    mr.upsert_media(c, "v1", "video", "a.mp4", "videos/a.mp4")
    pid = pr.create_playlist(c, "x")
    pr.update_playlist(c, pid, name="x", repeat_mode="off", shuffle=0,
                       blocks=[{"kind": "video", "video_id": "v1"}])
    mr.delete_media(c, "v1")
    assert mr.get_media(c, "v1") is None
    assert c.execute("SELECT COUNT(*) FROM playlist_blocks").fetchone()[0] == 0
