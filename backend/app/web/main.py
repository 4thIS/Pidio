# backend/app/web/main.py
"""FastAPI 앱 팩토리.

create_app(testing=False) 로 앱을 생성한다.
- /api/health : 헬스체크
- 정적 서빙  : Vue 빌드 산출물(app/static)을 SPA 로 마운트(테스트 모드에선 생략).
"""
from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.web.deps import Deps
from app.web import auth
from app.web.sse import StateHub, router as sse_router

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(testing: bool = False) -> FastAPI:
    app = FastAPI(title="Pidio")
    app.state.deps = Deps(testing=testing)
    app.state.hub = StateHub()

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    app.include_router(auth.router)
    app.include_router(sse_router)

    # 정적(SPA) 마운트는 실제 서빙 시에만. 테스트 모드에선 산출물이 없을 수 있어 생략.
    if not testing:
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    return app


# uvicorn app.web.main:app 진입점
app = create_app()
