# backend/app/web/routers/player.py
"""E-4 재생 제어 라우터 (Task 8.4) — AppService/Player 위임 + SSE 브로드캐스트.

모든 상태 변경 후 hub.publish(player.get_state()) 로 전 구독자에 방송.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.web.auth import require_session

router = APIRouter(prefix="/api", tags=["player"], dependencies=[Depends(require_session)])

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


# ---- 단순 동작 (마지막 선언) ----

@router.post("/player/{action}")
def player_action(action: str, request: Request) -> dict:
    fn = _SIMPLE.get(action)
    if fn is None:
        raise HTTPException(status_code=404, detail="unknown action")
    fn(request.app.state.deps)
    _publish(request)
    return {"ok": True}
