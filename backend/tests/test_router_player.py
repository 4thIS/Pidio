# backend/tests/test_router_player.py
"""E-4 재생 제어 라우터 (Task 8.4)."""
from fastapi.testclient import TestClient

from app.domain import media_repo
from app.web.main import create_app


def _client():
    app = create_app(testing=True)
    db = app.state.deps.db
    media_repo.upsert_media(db, "v1", "video", "a.mp4", "videos/v1.mp4", duration=10.0)
    media_repo.upsert_media(db, "v2", "video", "b.mp4", "videos/v2.mp4", duration=10.0)
    c = TestClient(app)
    c.post("/api/login", json={"password": "pw"})
    return c, app


def test_play_selection():
    c, app = _client()
    r = c.post("/api/play/selection", json={"content_ids": ["v1", "v2"], "repeat": "all", "shuffle": False})
    assert r.status_code == 200
    st = app.state.deps.player.get_state()
    assert st.queue_len == 2 and st.repeat == "all" and st.mode == "manual"


def test_player_actions_next_prev_pause_resume():
    c, app = _client()
    c.post("/api/play/selection", json={"content_ids": ["v1", "v2"]})
    p = app.state.deps.player
    c.post("/api/player/next")
    assert p.pos == 1
    c.post("/api/player/prev")
    assert p.pos == 0
    c.post("/api/player/pause")
    assert p.get_state().status == "paused"
    c.post("/api/player/resume")
    assert p.get_state().status == "playing"


def test_player_stop_and_resume_auto():
    c, app = _client()
    c.post("/api/play/selection", json={"content_ids": ["v1"]})
    assert c.post("/api/player/stop").status_code == 200
    assert app.state.deps.player.get_state().status == "standby"
    r = c.post("/api/player/resume_auto")
    assert r.status_code == 200
    assert app.state.deps.player.mode == "auto"


def test_player_jump_repeat_shuffle():
    c, app = _client()
    c.post("/api/play/selection", json={"content_ids": ["v1", "v2"]})
    p = app.state.deps.player
    c.post("/api/player/jump", json={"index": 1})
    assert p.pos == 1
    c.post("/api/player/repeat", json={"mode": "one"})
    assert p.repeat == "one"
    c.post("/api/player/shuffle", json={"on": True})
    assert p.shuffle is True


def test_player_queue_remove():
    c, app = _client()
    c.post("/api/play/selection", json={"content_ids": ["v1", "v2"]})
    c.post("/api/player/queue/remove", json={"index": 0})
    assert app.state.deps.player.get_state().queue_len == 1


def test_unknown_action_404():
    c, _ = _client()
    assert c.post("/api/player/frobnicate").status_code == 404


def test_player_requires_auth():
    app = create_app(testing=True)
    c = TestClient(app)
    assert c.post("/api/player/next").status_code == 401
    assert c.post("/api/play/selection", json={"content_ids": []}).status_code == 401
