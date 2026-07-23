# backend/tests/test_integration_phase8.py
"""Phase 8 통합 스모크 — 업로드→목록→플리→재생 전 구간이 실제로 맞물리는지."""
from fastapi.testclient import TestClient

from app.web.main import create_app


def _client(tmp_path):
    app = create_app(testing=True)
    usb = tmp_path / "usb"
    for sub in ("videos", "pictures", "music"):
        (usb / sub).mkdir(parents=True)
    app.state.deps.media_root = str(usb)
    app.state.deps.upload_tmp = str(tmp_path / "uptmp")
    c = TestClient(app)
    c.post("/api/login", json={"password": "pw"})
    return c, app


def test_upload_then_list_then_play(tmp_path):
    c, app = _client(tmp_path)
    data = b"pidio-integration-video-" + b"x" * 200

    # 1) 업로드 (init → chunk → complete)
    uid = c.post("/api/upload/init",
                 json={"filename": "clip.mp4", "size": len(data), "type": "video"}).json()["upload_id"]
    c.put(f"/api/upload/{uid}/chunk?index=0", content=data)
    cid = c.post(f"/api/upload/{uid}/complete").json()["content_id"]

    # 2) 미디어 목록에 등장 (upload 가 쓴 것을 media 라우터가 읽음 — 같은 DB)
    items = c.get("/api/media?type=video").json()
    assert any(m["content_id"] == cid and m["title"] == "clip.mp4" for m in items)

    # 3) 이 미디어로 플레이리스트 구성 → 저장 → 재생
    pid = c.post("/api/playlists", json={"name": "통합"}).json()["id"]
    c.put(f"/api/playlists/{pid}",
          json={"name": "통합", "repeat_mode": "off", "shuffle": False,
                "blocks": [{"kind": "video", "video_id": cid}]})
    assert c.post(f"/api/playlists/{pid}/play").status_code == 200

    # 4) 도메인 Player 상태에 반영
    st = app.state.deps.player.get_state()
    assert st.queue_len == 1 and st.source_label == "통합" and st.mode == "manual"

    # 5) 스트리밍으로 실제 파일이 되돌아옴(Range)
    r = c.get(f"/stream/{cid}", headers={"Range": "bytes=0-9"})
    assert r.status_code == 206 and r.content == data[:10]
