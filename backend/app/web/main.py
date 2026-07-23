# backend/app/web/main.py
"""FastAPI 앱 팩토리.

create_app(testing=False) 로 앱을 생성한다.
- /api/health : 헬스체크
- 정적 서빙  : Vue 빌드 산출물(app/static)을 SPA 로 마운트(테스트 모드에선 생략).
"""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.web.deps import Deps
from app.web import auth
from app.web.background import run_loop, startup_scan
from app.web.sse import StateHub, router as sse_router
from app.web.upload import router as upload_router
from app.web.streaming import router as streaming_router
from app.web.routers.media import router as media_router
from app.web.routers.playlists import router as playlists_router
from app.web.routers.schedule import router as schedule_router
from app.web.routers.player import router as player_router
from app.web.routers.settings import router as settings_router

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # 부팅 시 이미 마운트된 미디어를 1회 스캔(목록/자동재생 준비).
    startup_scan(app.state.deps)
    # 분 단위 스케줄 틱 루프 기동(운영 시에만).
    task = asyncio.create_task(run_loop(app.state.deps, app.state.hub))
    try:
        yield
    finally:
        task.cancel()


def create_app(testing: bool = False) -> FastAPI:
    # 테스트 모드에선 백그라운드 루프를 띄우지 않는다.
    app = FastAPI(title="Pidio", lifespan=None if testing else _lifespan)
    app.state.deps = Deps(testing=testing)
    app.state.hub = StateHub()

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    app.include_router(auth.router)
    app.include_router(sse_router)
    app.include_router(upload_router)
    app.include_router(streaming_router)
    app.include_router(media_router)
    app.include_router(playlists_router)
    app.include_router(schedule_router)
    app.include_router(player_router)
    app.include_router(settings_router)

    # 정적(SPA) 마운트는 실제 서빙 시에만. 테스트 모드에선 산출물이 없을 수 있어 생략.
    if not testing:
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    return app


# uvicorn app.web.main:app 진입점
app = create_app()
