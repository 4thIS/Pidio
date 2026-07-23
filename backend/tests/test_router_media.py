# backend/tests/test_router_media.py
"""E-1 미디어 라우터 (Task 8.1)."""
from fastapi.testclient import TestClient

from app.domain import media_repo
from app.web.main import create_app


def _client():
    app = create_app(testing=True)
    db = app.state.deps.db
    media_repo.upsert_media(db, "v1", "video", "clip.mp4", "videos/v1.mp4", duration=12.0)
    media_repo.upsert_media(db, "p1", "photo", "pic.jpg", "pictures/p1.jpg")
    media_repo.upsert_media(db, "a1", "music", "song.mp3", "music/a1.mp3", duration=200.0)
    c = TestClient(app)
    c.post("/api/login", json={"password": "pw"})
    return c, app


def test_list_media_all():
    c, _ = _client()
    r = c.get("/api/media")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 3
    v = next(m for m in items if m["content_id"] == "v1")
    assert v["media_type"] == "video"
    assert v["title"] == "clip.mp4"          # custom_title 없으면 original_name
    assert v["duration"] == 12.0
    assert v["available"] is True
    assert v["thumb_url"] == "/thumb/v1"


def test_list_media_filter_type():
    c, _ = _client()
    r = c.get("/api/media?type=music")
    assert [m["content_id"] for m in r.json()] == ["a1"]


def test_patch_title_uses_custom():
    c, app = _client()
    r = c.patch("/api/media/v1", json={"custom_title": "졸업영상"})
    assert r.status_code == 200
    row = media_repo.get_media(app.state.deps.db, "v1")
    assert row["custom_title"] == "졸업영상"
    # 목록에서 title 이 custom 으로 반영
    got = next(m for m in c.get("/api/media").json() if m["content_id"] == "v1")
    assert got["title"] == "졸업영상"


def test_media_requires_auth():
    app = create_app(testing=True)
    c = TestClient(app)  # 로그인 안 함
    assert c.get("/api/media").status_code == 401
