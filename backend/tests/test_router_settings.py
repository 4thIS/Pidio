# backend/tests/test_router_settings.py
"""E-5 설정 라우터 & 스캔 (Task 8.5)."""
import os

from fastapi.testclient import TestClient

from app.domain import media_repo
from app.web.main import create_app


def _client():
    app = create_app(testing=True)
    c = TestClient(app)
    c.post("/api/login", json={"password": "orig-pw"})
    return c, app


def test_get_defaults():
    c, _ = _client()
    s = c.get("/api/settings").json()
    assert s["default_playlist_id"] is None
    assert s["photo_default_sec"] == 5


def test_put_and_get_roundtrip():
    c, _ = _client()
    pid = c.post("/api/playlists", json={"name": "기본"}).json()["id"]
    r = c.put("/api/settings", json={"default_playlist_id": pid, "photo_default_sec": 8})
    assert r.status_code == 200
    s = c.get("/api/settings").json()
    assert s["default_playlist_id"] == pid and s["photo_default_sec"] == 8


def test_change_password():
    c, app = _client()
    # 틀린 현재 비번 → 401
    assert c.post("/api/settings/password", json={"old": "wrong", "new": "n"}).status_code == 401
    # 올바른 현재 비번 → 200, 이후 새 비번으로 재로그인 가능
    assert c.post("/api/settings/password", json={"old": "orig-pw", "new": "new-pw"}).status_code == 200
    c2 = TestClient(app)
    assert c2.post("/api/login", json={"password": "new-pw"}).status_code == 200
    assert c2.post("/api/login", json={"password": "orig-pw"}).status_code == 401


def test_rescan_finds_files(tmp_path):
    c, app = _client()
    usb = tmp_path / "usb"
    (usb / "videos").mkdir(parents=True)
    (usb / "videos" / "a.mp4").write_bytes(b"x" * 20)
    app.state.deps.media_root = str(usb)
    r = c.post("/api/rescan")
    assert r.status_code == 200
    assert r.json()["seen"] == 1
    assert len(media_repo.list_media(app.state.deps.db, "video")) == 1


def test_rescan_unmounted_409():
    c, app = _client()
    app.state.deps.media_root = "/no/such/path/xyz"
    assert c.post("/api/rescan").status_code == 409


def test_settings_require_auth():
    app = create_app(testing=True)
    c = TestClient(app)
    assert c.get("/api/settings").status_code == 401
