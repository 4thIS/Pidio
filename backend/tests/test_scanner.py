import os

from app.domain import media_repo as mr
from app.domain import scanner
from app.domain.db import connect, init_db


def _mk(root, rel, data=b"x" * 10):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    return p


def _conn(tmp_path):
    c = connect(str(tmp_path / "t.sqlite3"))
    init_db(c)
    return c


# 테스트에선 실제 해시 대신 파일명을 id로(결정적·간단)
_ID = lambda p: os.path.basename(p)


def test_scan_classifies_types(tmp_path):
    usb = str(tmp_path / "usb")
    _mk(usb, "videos/a.mp4")
    _mk(usb, "pictures/b.jpg")
    _mk(usb, "music/c.mp3")
    c = _conn(tmp_path)
    scanner.scan_library(c, usb, id_fn=_ID)
    types = {m["content_id"]: m["media_type"] for m in mr.list_media(c, None)}
    assert types == {"a.mp4": "video", "b.jpg": "photo", "c.mp3": "music"}


def test_ignores_unknown_extensions(tmp_path):
    usb = str(tmp_path / "usb")
    _mk(usb, "videos/a.mp4")
    _mk(usb, "videos/readme.txt")  # 미디어 아님 → 무시
    c = _conn(tmp_path)
    scanner.scan_library(c, usb, id_fn=_ID)
    assert {m["content_id"] for m in mr.list_media(c, None)} == {"a.mp4"}


def test_scans_nested_subfolders(tmp_path):
    usb = str(tmp_path / "usb")
    _mk(usb, "videos/2026/행사/a.mp4")
    c = _conn(tmp_path)
    scanner.scan_library(c, usb, id_fn=_ID)
    m = mr.get_media(c, "a.mp4")
    assert m is not None
    assert m["rel_path"] == "videos/2026/행사/a.mp4"  # 슬래시 정규화


def test_removed_file_marked_unavailable_on_rescan(tmp_path):
    usb = str(tmp_path / "usb")
    v = _mk(usb, "videos/a.mp4")
    c = _conn(tmp_path)
    scanner.scan_library(c, usb, id_fn=_ID)
    os.remove(v)
    scanner.scan_library(c, usb, id_fn=_ID)
    assert mr.get_media(c, "a.mp4")["available"] == 0


def test_returns_added_and_seen(tmp_path):
    usb = str(tmp_path / "usb")
    _mk(usb, "videos/a.mp4")
    _mk(usb, "pictures/b.jpg")
    c = _conn(tmp_path)
    r1 = scanner.scan_library(c, usb, id_fn=_ID)
    assert set(r1["added"]) == {"a.mp4", "b.jpg"}
    assert r1["seen"] == 2
    # 재스캔 시 added 비어야(이미 알던 것)
    r2 = scanner.scan_library(c, usb, id_fn=_ID)
    assert r2["added"] == []
    assert r2["seen"] == 2


def test_missing_usb_folder_does_not_crash(tmp_path):
    usb = str(tmp_path / "usb")  # 폴더 자체가 없음(USB 미마운트 상황)
    c = _conn(tmp_path)
    r = scanner.scan_library(c, usb, id_fn=_ID)
    assert r == {"added": [], "seen": 0}
