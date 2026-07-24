# backend/app/web/background.py
"""E-6 백그라운드 스케줄 루프 (Task 8.6).

분 단위 틱으로 스케줄을 재평가(수동 모드면 도메인이 무시)하고, 상태를 SSE로 방송한다.
USB 마운트 상태가 미마운트→마운트로 바뀌면 재스캔한다.
lifespan 에서 asyncio 태스크로 기동된다.
"""
from __future__ import annotations

import asyncio
import os

from pathlib import Path

from app.domain import media_repo, scanner
from app.web import media_tools

_TICK_SECONDS = 60


def process_added(deps, added_ids) -> None:
    """스캔으로 새로 발견된 파일에 길이/썸네일 생성(업로드 안 거친 USB 파일용)."""
    if not added_ids:
        return
    thumb_dir = Path(deps.media_root) / ".pidio" / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    for cid in added_ids:
        m = media_repo.get_media(deps.db, cid)
        if not m or not m["rel_path"]:
            continue
        import os as _os
        path = _os.path.join(deps.media_root, m["rel_path"])
        if m["media_type"] in ("video", "music"):
            dur = media_tools.probe_duration(path)
            if dur is not None:
                media_repo.upsert_media(deps.db, cid, m["media_type"],
                                        m["original_name"], m["rel_path"], duration=dur)
        if m["media_type"] in ("video", "photo"):
            thumb = thumb_dir / f"{cid}.jpg"
            if not thumb.exists():
                media_tools.make_thumbnail(path, str(thumb))


def startup_scan(deps) -> int:
    """부팅 시 media_root 가 마운트돼 있으면 1회 스캔. 발견한 미디어 수 반환.

    (백그라운드 루프는 마운트 '전환' 시에만 스캔하므로, 이미 마운트된 채 부팅한
    경우를 여기서 처리한다 — 부팅 자동재생/목록 표시에 필요.)
    """
    if not os.path.isdir(deps.media_root):
        return 0
    result = scanner.scan_library(deps.db, deps.media_root)
    process_added(deps, result["added"])
    return result["seen"]


def tick(deps, hub, now=None) -> None:
    """한 번의 틱: 스케줄 재평가 + 상태 방송."""
    deps.service.evaluate_schedule(now)
    hub.publish(deps.player.get_state())


def maybe_rescan(deps, was_mounted: bool) -> bool:
    """USB 미마운트→마운트 전환 시 재스캔. 현재 마운트 여부 반환."""
    mounted = os.path.isdir(deps.media_root)
    if mounted and not was_mounted:
        result = scanner.scan_library(deps.db, deps.media_root)
        process_added(deps, result["added"])
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


def position_tick(deps, hub) -> None:
    """재생 중이면 time-pos/duration 갱신 후 상태 방송(진행바)."""
    if deps.player.status == "playing":
        deps.player.refresh_position()
        hub.publish(deps.player.get_state())


async def run_position_loop(deps, hub, interval: float = 1.0) -> None:
    """1초 주기로 진행바 갱신 방송. mpv get_property는 블로킹이라 executor로."""
    loop = asyncio.get_event_loop()
    try:
        while True:
            await asyncio.sleep(interval)
            await loop.run_in_executor(None, position_tick, deps, hub)
    except asyncio.CancelledError:
        pass
