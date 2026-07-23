# backend/tests/test_router_playlists.py
"""E-2 플레이리스트 라우터 (Task 8.2)."""
from fastapi.testclient import TestClient

from app.domain import media_repo
from app.web.main import create_app


def _client():
    app = create_app(testing=True)
    db = app.state.deps.db
    media_repo.upsert_media(db, "v1", "video", "a.mp4", "videos/v1.mp4", duration=10.0)
    media_repo.upsert_media(db, "p1", "photo", "b.jpg", "pictures/p1.jpg")
    media_repo.upsert_media(db, "a1", "music", "c.mp3", "music/a1.mp3", duration=100.0)
    c = TestClient(app)
    c.post("/api/login", json={"password": "pw"})
    return c, app


def test_create_list_get_delete():
    c, _ = _client()
    pid = c.post("/api/playlists", json={"name": "졸업식"}).json()["id"]
    assert pid
    lst = c.get("/api/playlists").json()
    assert any(p["id"] == pid and p["name"] == "졸업식" for p in lst)
    got = c.get(f"/api/playlists/{pid}").json()
    assert got["name"] == "졸업식" and got["blocks"] == []
    assert c.delete(f"/api/playlists/{pid}").status_code == 200
    assert all(p["id"] != pid for p in c.get("/api/playlists").json())


def test_blocks_roundtrip():
    c, _ = _client()
    pid = c.post("/api/playlists", json={"name": "행사"}).json()["id"]
    blocks = [
        {"kind": "video", "video_id": "v1"},
        {"kind": "slideshow", "music_id": "a1",
         "photos": [{"photo_id": "p1", "duration_sec": 7}]},
    ]
    r = c.put(f"/api/playlists/{pid}",
              json={"name": "행사", "repeat_mode": "all", "shuffle": False, "blocks": blocks})
    assert r.status_code == 200
    got = c.get(f"/api/playlists/{pid}").json()
    assert got["repeat_mode"] == "all"
    assert got["blocks"][0] == {"kind": "video", "video_id": "v1"}
    assert got["blocks"][1]["kind"] == "slideshow"
    assert got["blocks"][1]["music_id"] == "a1"
    assert got["blocks"][1]["photos"][0]["photo_id"] == "p1"
    assert got["blocks"][1]["photos"][0]["duration_sec"] == 7


def test_play_playlist_sets_player():
    c, app = _client()
    pid = c.post("/api/playlists", json={"name": "P"}).json()["id"]
    c.put(f"/api/playlists/{pid}",
          json={"name": "P", "repeat_mode": "off", "shuffle": False,
                "blocks": [{"kind": "video", "video_id": "v1"}]})
    r = c.post(f"/api/playlists/{pid}/play")
    assert r.status_code == 200
    st = app.state.deps.player.get_state()
    assert st.queue_len == 1 and st.source_label == "P" and st.mode == "manual"


def test_playlists_require_auth():
    app = create_app(testing=True)
    c = TestClient(app)
    assert c.get("/api/playlists").status_code == 401
