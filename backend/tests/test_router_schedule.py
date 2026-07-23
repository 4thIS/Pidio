# backend/tests/test_router_schedule.py
"""E-3 예약 라우터 (Task 8.3)."""
from fastapi.testclient import TestClient

from app.web.main import create_app


def _client():
    app = create_app(testing=True)
    c = TestClient(app)
    c.post("/api/login", json={"password": "pw"})
    return c


def _pl(c, name):
    return c.post("/api/playlists", json={"name": name}).json()["id"]


WEEKLY = {"sched_type": "weekly", "weekdays": "mon,tue", "start_time": "12:00", "end_time": "13:00"}


def test_set_and_get_schedule():
    c = _client()
    pid = _pl(c, "점심")
    r = c.put(f"/api/playlists/{pid}/schedule", json=WEEKLY)
    assert r.status_code == 200
    got = c.get(f"/api/playlists/{pid}").json()
    assert got["schedule"]["sched_type"] == "weekly"
    assert got["schedule"]["weekdays"] == "mon,tue"


def test_overlap_returns_409():
    c = _client()
    p1 = _pl(c, "점심1")
    c.put(f"/api/playlists/{p1}/schedule", json=WEEKLY)
    p2 = _pl(c, "점심2")
    overlap = {"sched_type": "weekly", "weekdays": "tue,wed", "start_time": "12:30", "end_time": "13:30"}
    r = c.put(f"/api/playlists/{p2}/schedule", json=overlap)
    assert r.status_code == 409


def test_delete_schedule():
    c = _client()
    pid = _pl(c, "점심")
    c.put(f"/api/playlists/{pid}/schedule", json=WEEKLY)
    assert c.delete(f"/api/playlists/{pid}/schedule").status_code == 200
    assert c.get(f"/api/playlists/{pid}").json()["schedule"] is None


def test_schedule_requires_auth():
    app = create_app(testing=True)
    c = TestClient(app)
    assert c.put("/api/playlists/1/schedule", json=WEEKLY).status_code == 401
