from app.domain import folder_repo as fr
from app.domain import media_repo as mr
from app.domain.db import connect, init_db


def _c(tmp):
    c = connect(str(tmp / "t.sqlite3"))
    init_db(c)
    return c


def _seed(c):
    mr.upsert_media(c, "v1", "video", "a.mp4", "videos/a.mp4", duration=10)
    mr.upsert_media(c, "p1", "photo", "1.jpg", "pictures/1.jpg")
    mr.upsert_media(c, "m1", "music", "s.mp3", "music/s.mp3", duration=200)


def test_create_list_and_count(tmp_path):
    c = _c(tmp_path)
    _seed(c)
    fid = fr.create_folder(c, "졸업식")
    fr.add_items(c, fid, ["v1", "p1"])
    folders = fr.list_folders(c)
    assert folders == [{"id": fid, "name": "졸업식", "item_count": 2}]


def test_add_items_dedup_and_only_existing(tmp_path):
    c = _c(tmp_path)
    _seed(c)
    fid = fr.create_folder(c, "f")
    fr.add_items(c, fid, ["v1", "v1", "nope"])  # 중복·없는 미디어 무시
    assert fr.content_ids(c, fid) == ["v1"]


def test_multi_membership(tmp_path):
    c = _c(tmp_path)
    _seed(c)
    a = fr.create_folder(c, "A")
    b = fr.create_folder(c, "B")
    fr.add_items(c, a, ["v1"])
    fr.add_items(c, b, ["v1"])  # 한 미디어가 여러 폴더에 소속 가능
    assert fr.content_ids(c, a) == ["v1"]
    assert fr.content_ids(c, b) == ["v1"]


def test_remove_item(tmp_path):
    c = _c(tmp_path)
    _seed(c)
    fid = fr.create_folder(c, "f")
    fr.add_items(c, fid, ["v1", "p1"])
    fr.remove_item(c, fid, "v1")
    assert fr.content_ids(c, fid) == ["p1"]


def test_delete_folder_keeps_media(tmp_path):
    c = _c(tmp_path)
    _seed(c)
    fid = fr.create_folder(c, "f")
    fr.add_items(c, fid, ["v1"])
    fr.delete_folder(c, fid)
    assert fr.list_folders(c) == []
    assert mr.get_media(c, "v1") is not None  # 파일(메타)은 유지


def test_deleting_media_cleans_folder_membership(tmp_path):
    c = _c(tmp_path)
    _seed(c)
    fid = fr.create_folder(c, "f")
    fr.add_items(c, fid, ["v1", "p1"])
    mr.delete_media(c, "v1")  # 미디어 삭제 → 폴더 소속도 정리
    assert fr.content_ids(c, fid) == ["p1"]


def test_reorder_folders(tmp_path):
    c = _c(tmp_path)
    a = fr.create_folder(c, "A")
    b = fr.create_folder(c, "B")
    d = fr.create_folder(c, "C")
    fr.reorder_folders(c, [d, b, a])  # C, B, A 순
    assert [f["name"] for f in fr.list_folders(c)] == ["C", "B", "A"]


def test_create_folder_orders_by_creation(tmp_path):
    c = _c(tmp_path)
    fr.create_folder(c, "A")
    fr.create_folder(c, "B")
    assert [f["name"] for f in fr.list_folders(c)] == ["A", "B"]


def test_get_folder_shape(tmp_path):
    c = _c(tmp_path)
    _seed(c)
    fid = fr.create_folder(c, "졸업")
    fr.add_items(c, fid, ["v1", "m1"])
    f = fr.get_folder(c, fid)
    assert f["id"] == fid and f["name"] == "졸업"
    assert set(f["content_ids"]) == {"v1", "m1"}
    assert fr.get_folder(c, 999) is None
