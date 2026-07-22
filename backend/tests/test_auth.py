# backend/tests/test_auth.py
from fastapi.testclient import TestClient
from app.web.main import create_app


def client() -> TestClient:
    return TestClient(create_app(testing=True))


def test_first_login_sets_password():
    # 초기 비번 미설정 → 최초 로그인이 비번을 설정하고 인증까지 성립.
    c = client()
    r = c.post("/api/login", json={"password": "secret123"})
    assert r.status_code == 200
    assert c.get("/api/me").status_code == 200


def test_protected_requires_cookie():
    # 쿠키 없으면 보호 엔드포인트 401.
    c = client()
    assert c.get("/api/me").status_code == 401


def test_wrong_password_401():
    c = client()
    c.post("/api/login", json={"password": "secret123"})  # 최초 로그인으로 비번 설정
    c.post("/api/logout")
    r = c.post("/api/login", json={"password": "wrong"})
    assert r.status_code == 401


def test_logout_clears_session():
    c = client()
    c.post("/api/login", json={"password": "secret123"})
    assert c.get("/api/me").status_code == 200
    c.post("/api/logout")
    assert c.get("/api/me").status_code == 401


def test_rate_limit_after_5_failures():
    c = client()
    c.post("/api/login", json={"password": "secret123"})  # 비번 설정
    c.post("/api/logout")
    for _ in range(5):
        assert c.post("/api/login", json={"password": "nope"}).status_code == 401
    # 5회 실패 누적 후 다음 시도는 429.
    assert c.post("/api/login", json={"password": "nope"}).status_code == 429
