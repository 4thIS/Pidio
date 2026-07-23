# backend/app/web/background.py
"""E-6 백그라운드 스케줄 루프 (Task 8.6).

분 단위 틱으로 스케줄을 재평가(수동 모드면 도메인이 무시)하고, 상태를 SSE로 방송한다.
USB 마운트 상태가 미마운트→마운트로 바뀌면 재스캔한다.
lifespan 에서 asyncio 태스크로 기동된다.
"""
from __future__ import annotations

import asyncio
import os

from app.domain import scanner

_TICK_SECONDS = 60


def tick(deps, hub, now=None) -> None:
    """한 번의 틱: 스케줄 재평가 + 상태 방송."""
    deps.service.evaluate_schedule(now)
    hub.publish(deps.player.get_state())


def maybe_rescan(deps, was_mounted: bool) -> bool:
    """USB 미마운트→마운트 전환 시 재스캔. 현재 마운트 여부 반환."""
    mounted = os.path.isdir(deps.media_root)
    if mounted and not was_mounted:
        scanner.scan_library(deps.db, deps.media_root)
    return mounted


async def run_loop(deps, hub, interval: int = _TICK_SECONDS) -> None:
    """앱 수명 동안 도는 루프. 취소되면 조용히 종료."""
    was_mounted = os.path.isdir(deps.media_root)
    try:
        while True:
            was_mounted = maybe_rescan(deps, was_mounted)
            tick(deps, hub)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass
