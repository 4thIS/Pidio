# backend/tests/test_web_boot.py
from fastapi.testclient import TestClient
from app.web.main import create_app


def test_health():
    c = TestClient(create_app(testing=True))
    assert c.get("/api/health").json() == {"ok": True}
