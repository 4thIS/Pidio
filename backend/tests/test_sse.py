# backend/tests/test_sse.py
import asyncio
import json

import pytest

from app.domain.contracts import PlayerState
from app.web.main import create_app
from app.web.sse import StateHub, events, format_sse


STATE = PlayerState(
    status="standby", mode="auto", repeat="off", shuffle=False,
    queue_len=0, current_index=0, current_title=None,
    source_label=None, position_sec=0.0, duration_sec=0.0,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_format_sse_is_data_line():
    line = format_sse(STATE)
    assert line.startswith("data: ")
    assert line.endswith("\n\n")
    assert json.loads(line[len("data: "):].strip())["status"] == "standby"


@pytest.mark.anyio
async def test_hub_fans_out_to_subscriber(anyio_backend):
    hub = StateHub()
    agen = hub.subscribe()
    task = asyncio.create_task(agen.__anext__())
    await asyncio.sleep(0)  # 구독 등록 기회
    hub.publish(STATE)
    received = await asyncio.wait_for(task, timeout=1)
    assert received == STATE
    await agen.aclose()


class _FakeRequest:
    def __init__(self, app):
        self.app = app


@pytest.mark.anyio
async def test_events_endpoint_pushes_state(anyio_backend):
    # /events 가 만드는 StreamingResponse 의 본문 제너레이터를 직접 구동해
    # (hub 구독 → 발행 → data: 라인) 경로를 검증한다. 무한 스트림이라 HTTP
    # 트랜스포트로 읽으면 버퍼링/hang 되므로 body_iterator 를 직접 소비.
    app = create_app(testing=True)
    resp = await events(_FakeRequest(app))
    assert resp.media_type == "text/event-stream"

    agen = resp.body_iterator
    task = asyncio.create_task(agen.__anext__())
    await asyncio.sleep(0)  # 구독 등록 기회
    app.state.hub.publish(STATE)
    chunk = await asyncio.wait_for(task, timeout=2)
    await agen.aclose()

    text = chunk.decode() if isinstance(chunk, (bytes, bytearray)) else chunk
    assert text.startswith("data: ")
    payload = json.loads(text[len("data: "):])
    assert payload["status"] == "standby"
