# backend/app/web/sse.py
"""SSE 상태 스트림.

GET /events 로 PlayerState(JSON)를 상태 변경 시 push 한다.
StateHub 가 asyncio.Queue 팬아웃으로 각 연결에 브로드캐스트.
AppService(도메인)가 상태 변경 시 hub.publish(state) 를 호출하면 된다.
"""
from __future__ import annotations
import asyncio
import json
from dataclasses import asdict
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.domain.contracts import PlayerState

router = APIRouter(tags=["sse"])


class StateHub:
    """구독자 큐 집합으로의 상태 팬아웃."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def subscribe(self) -> AsyncIterator[PlayerState]:
        # 이벤트 루프를 기록해 다른 스레드(예: 스케줄러)에서의 publish 를 안전하게 넘긴다.
        self._loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subscribers.discard(q)

    def publish(self, state: PlayerState) -> None:
        """상태를 모든 구독자에게 전달. 어느 스레드에서 호출해도 안전."""
        loop = self._loop
        for q in list(self._subscribers):
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(q.put_nowait, state)
            else:
                q.put_nowait(state)


def format_sse(state: PlayerState) -> str:
    return f"data: {json.dumps(asdict(state))}\n\n"


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    hub: StateHub = request.app.state.hub

    async def gen() -> AsyncIterator[str]:
        async for state in hub.subscribe():
            yield format_sse(state)

    return StreamingResponse(gen(), media_type="text/event-stream")
