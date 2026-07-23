# backend/tests/test_streaming.py
"""Task 7.3 Range 스트리밍 & 썸네일 서빙 테스트.

content_id → 경로는 media_store(rel_path) + media_root 로 해석.
"""
from fastapi.testclient import TestClient

from app.web.main import create_app


def _app(tmp_path):
    app = create_app(testing=True)
    app.state.deps.media_root = str(tmp_path / "usb")
    return TestClient(app), app, tmp_path / "usb"


def _register_video(app, usb, content_id="cid", data=b"0123456789ABCDEF"):
    from app.domain import media_repo
    (usb / "videos").mkdir(parents=True, exist_ok=True)
    (usb / "videos" / f"{content_id}.mp4").write_bytes(data)
    media_repo.upsert_media(app.state.deps.db, content_id, "video", "clip.mp4", f"videos/{content_id}.mp4")
    return data


def test_stream_range_returns_206_partial(tmp_path):
    client, app, usb = _app(tmp_path)
    data = _register_video(app, usb)
    r = client.get("/stream/cid", headers={"Range": "bytes=0-3"})
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 0-3/{len(data)}"
    assert r.headers["accept-ranges"] == "bytes"
    assert r.content == data[:4]


def test_stream_full_when_no_range(tmp_path):
    client, app, usb = _app(tmp_path)
    data = _register_video(app, usb)
    r = client.get("/stream/cid")
    assert r.status_code == 200
    assert r.content == data


def test_stream_missing_id_404(tmp_path):
    client, app, usb = _app(tmp_path)
    assert client.get("/stream/nope").status_code == 404


def test_thumb_serves_jpeg(tmp_path):
    client, app, usb = _app(tmp_path)
    _register_video(app, usb)
    thumbs = usb / ".pidio" / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    (thumbs / "cid.jpg").write_bytes(b"\xff\xd8\xff\xe0jpeg-bytes")
    r = client.get("/thumb/cid")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.content.startswith(b"\xff\xd8")


def test_thumb_missing_id_404(tmp_path):
    client, app, usb = _app(tmp_path)
    assert client.get("/thumb/nope").status_code == 404
