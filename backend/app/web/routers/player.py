# backend/app/web/routers/player.py
"""E-4 재생 제어 라우터 (Task 8.4) — AppService/Player 위임 + SSE 브로드캐스트.

모든 상태 변경 후 hub.publish(player.get_state()) 로 전 구독자에 방송.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.domain import media_repo, playlist_repo
from app.domain.service import _block_to_dict
from app.web.auth import require_session

router = APIRouter(prefix="/api", tags=["player"], dependencies=[Depends(require_session)])


@router.get("/player/queue")
def player_queue(request: Request) -> dict:
    deps = request.app.state.deps
    items = []
    for it in deps.player.queue_view():
        m = media_repo.get_media(deps.db, it["content_id"])
        items.append({
            "content_id": it["content_id"],
            "title": (m["custom_title"] or m["original_name"]) if m else it["content_id"],
            "thumb_url": (f"/thumb/{it['content_id']}"
                          if m and m["media_type"] != "music" else None),
            "kind": it["kind"],
            "media_type": m["media_type"] if m else None,
            "photo_sec": it["sec"],
            "current": it["current"],
        })
    src = None
    pid = deps.service.current_source_playlist_id
    if pid is not None:
        src = next((p for p in playlist_repo.list_playlists(deps.db) if p["id"] == pid), None)
    return {"source_playlist": src, "items": items}

# player 의 인자 없는 단순 동작.
_SIMPLE = {
    "next": lambda deps: deps.player.next(),
    "prev": lambda deps: deps.player.prev(),
    "pause": lambda deps: deps.player.pause(),
    "resume": lambda deps: deps.player.resume(),
    "stop": lambda deps: deps.player.stop_to_standby(),
    "resume_auto": lambda deps: deps.service.resume_auto(),
}


def _publish(request):
    deps = request.app.state.deps
    request.app.state.hub.publish(deps.player.get_state())


# ---- 선택 재생 ----

class SelectionBody(BaseModel):
    content_ids: list[str]
    repeat: str = "off"
    shuffle: bool = False


@router.post("/play/selection")
def play_selection(body: SelectionBody, request: Request) -> dict:
    deps = request.app.state.deps
    deps.service.play_selection(body.content_ids, repeat=body.repeat, shuffle=body.shuffle)
    _publish(request)
    return {"ok": True}


# ---- 구체 제어 (반드시 /{action} 보다 먼저 선언) ----

class JumpBody(BaseModel):
    index: int


@router.post("/player/jump")
def jump(body: JumpBody, request: Request) -> dict:
    request.app.state.deps.player.jump_to(body.index)
    _publish(request)
    return {"ok": True}


class RepeatBody(BaseModel):
    mode: str


@router.post("/player/repeat")
def repeat(body: RepeatBody, request: Request) -> dict:
    request.app.state.deps.player.set_repeat(body.mode)
    _publish(request)
    return {"ok": True}


class ShuffleBody(BaseModel):
    on: bool


@router.post("/player/shuffle")
def shuffle(body: ShuffleBody, request: Request) -> dict:
    request.app.state.deps.player.set_shuffle(body.on)
    _publish(request)
    return {"ok": True}


@router.post("/player/queue/reorder")
async def queue_reorder(request: Request) -> dict:
    # 프론트 계약이 예약어 'from' 키라 raw json 으로 받는다.
    data = await request.json()
    request.app.state.deps.player.reorder(int(data["from"]), int(data["to"]))
    _publish(request)
    return {"ok": True}


class RemoveBody(BaseModel):
    index: int


@router.post("/player/queue/remove")
def queue_remove(body: RemoveBody, request: Request) -> dict:
    request.app.state.deps.player.remove(body.index)
    _publish(request)
    return {"ok": True}


class PhotoSecBody(BaseModel):
    index: int
    sec: float


@router.post("/player/queue/photo_sec")
def queue_photo_sec(body: PhotoSecBody, request: Request) -> dict:
    request.app.state.deps.player.set_photo_duration(body.index, body.sec)
    _publish(request)
    return {"ok": True}


class SaveQueueBody(BaseModel):
    name: str = "새 목록"


@router.post("/player/queue/save")
def queue_save(body: SaveQueueBody, request: Request) -> dict:
    deps = request.app.state.deps
    pid = deps.service.save_queue_as_playlist(body.name.strip() or "새 목록")
    return {"id": pid}


@router.get("/player/queue/blocks")
def queue_blocks(request: Request) -> dict:
    """현재 큐를 블록 구조로 반환(타임라인 에디터 시드용)."""
    p = request.app.state.deps.player
    return {"blocks": [_block_to_dict(b) for b in p.queue],
            "repeat_mode": p.repeat, "shuffle": bool(p.shuffle)}


# ---- 단순 동작 (마지막 선언) ----

@router.post("/player/{action}")
def player_action(action: str, request: Request) -> dict:
    fn = _SIMPLE.get(action)
    if fn is None:
        raise HTTPException(status_code=404, detail="unknown action")
    fn(request.app.state.deps)
    _publish(request)
    return {"ok": True}


@router.post("/player/queue/add")
async def queue_add(request: Request) -> dict:
    deps = request.app.state.deps
    data = await request.json()
    blocks = playlist_repo.selection_to_blocks(deps.db, data.get("content_ids", []))
    deps.player.enqueue(blocks)
    _publish(request)
    return {"ok": True}
