# backend/app/web/auth.py
"""세션 인증(공용 비번).

- 비번은 pbkdf2-hmac-sha256 해시로 settings.password_hash 에 저장.
- 세션은 표준 hmac 서명 쿠키(외부 의존성 없음).
- 최초 로그인 시 비번이 설정된다.
- 연속 실패 5회 누적 후에는 429(rate limit).
"""
from __future__ import annotations
import hashlib
import hmac
import os
import secrets
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

COOKIE_NAME = "session"
_SESSION_MARKER = "v1"          # 서명 대상 페이로드(공용 세션 표식)
_PBKDF2_ITERATIONS = 200_000
_MAX_FAILS = 5

router = APIRouter(prefix="/api", tags=["auth"])


# ---- settings 헬퍼 --------------------------------------------------------

def get_setting(db: sqlite3.Connection, key: str) -> str | None:
    row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(db: sqlite3.Connection, key: str, value: str) -> None:
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    db.commit()


# ---- 비번 해시 ------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iters)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)


# ---- 세션 서명 쿠키 -------------------------------------------------------

def _session_secret(db: sqlite3.Connection) -> bytes:
    """서명 비밀키. 없으면 생성해 저장(재시작 후에도 세션 유지)."""
    secret = get_setting(db, "session_secret")
    if secret is None:
        secret = secrets.token_hex(32)
        set_setting(db, "session_secret", secret)
    return secret.encode()


def _sign(secret: bytes, value: str) -> str:
    sig = hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{sig}"


def _valid_token(secret: bytes, token: str | None) -> bool:
    if not token or "." not in token:
        return False
    value, _, sig = token.rpartition(".")
    expected = hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


def require_session(request: Request) -> None:
    """보호 엔드포인트용 의존성. 유효 세션 쿠키가 없으면 401."""
    deps = request.app.state.deps
    token = request.cookies.get(COOKIE_NAME)
    if not _valid_token(_session_secret(deps.db), token):
        raise HTTPException(status_code=401, detail="Not authenticated")


# ---- 라우트 ---------------------------------------------------------------

class LoginBody(BaseModel):
    password: str


def _set_session_cookie(response: Response, db: sqlite3.Connection) -> None:
    token = _sign(_session_secret(db), _SESSION_MARKER)
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax", path="/"
    )


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response) -> dict:
    deps = request.app.state.deps
    db = deps.db

    if deps.login_fails >= _MAX_FAILS:
        raise HTTPException(status_code=429, detail="Too many attempts")

    stored = get_setting(db, "password_hash")
    if stored is None:
        # 최초 로그인: 이 비번으로 설정하고 인증 성립.
        set_setting(db, "password_hash", hash_password(body.password))
        deps.login_fails = 0
        _set_session_cookie(response, db)
        return {"ok": True, "first_login": True}

    if not verify_password(body.password, stored):
        deps.login_fails += 1
        raise HTTPException(status_code=401, detail="Invalid password")

    deps.login_fails = 0
    _set_session_cookie(response, db)
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(_: None = Depends(require_session)) -> dict:
    return {"authenticated": True}
