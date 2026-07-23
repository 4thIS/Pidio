# backend/tests/test_upload.py
"""Task 7.2 청크 업로드 테스트.

가짜 어댑터(deps.media_store / deps.compute_content_id) 위에서 검증.
USB 루트(media_root) 존재 = 마운트됨, 부재 = 409.
"""
from fastapi.testclient import TestClient

from app.web.main import create_app


def _make(tmp_path, mounted=True):
    app = create_app(testing=True)
    usb = tmp_path / "usb"
    if mounted:
        for sub in ("videos", "pictures", "music"):
            (usb / sub).mkdir(parents=True)
    app.state.deps.media_root = str(usb)
    app.state.deps.upload_tmp = str(tmp_path / "uptmp")
    client = TestClient(app)
    client.post("/api/login", json={"password": "pw"})  # 최초 로그인 → 세션 쿠키
    return client, app, usb


def test_chunked_upload_creates_file_and_media_row(tmp_path):
    client, app, usb = _make(tmp_path)
    data = b"hello-pidio-video-content-0123456789"

    r = client.post("/api/upload/init",
                    json={"filename": "clip.mp4", "size": len(data), "type": "video"})
    assert r.status_code == 200
    uid = r.json()["upload_id"]

    mid = len(data) // 2
    assert client.put(f"/api/upload/{uid}/chunk?index=0", content=data[:mid]).status_code == 200
    assert client.put(f"/api/upload/{uid}/chunk?index=1", content=data[mid:]).status_code == 200

    r = client.post(f"/api/upload/{uid}/complete")
    assert r.status_code == 200
    cid = r.json()["content_id"]
    assert cid

    # 최종 파일이 videos/ 아래에 하나 존재하고 내용이 원본과 동일
    files = list((usb / "videos").iterdir())
    assert len(files) == 1
    assert files[0].read_bytes() == data

    # 미디어 행 생성됨(실 DB)
    from app.domain import media_repo
    row = media_repo.get_media(app.state.deps.db, cid)
    assert row is not None and row["media_type"] == "video"


def test_complete_without_mount_returns_409(tmp_path):
    client, app, usb = _make(tmp_path, mounted=False)  # usb 디렉토리 없음 = 미마운트
    uid = client.post("/api/upload/init",
                      json={"filename": "a.mp4", "size": 3, "type": "video"}).json()["upload_id"]
    client.put(f"/api/upload/{uid}/chunk?index=0", content=b"xyz")
    r = client.post(f"/api/upload/{uid}/complete")
    assert r.status_code == 409


def test_upload_requires_auth(tmp_path):
    app = create_app(testing=True)
    app.state.deps.media_root = str(tmp_path / "usb")
    app.state.deps.upload_tmp = str(tmp_path / "uptmp")
    client = TestClient(app)  # 로그인 안 함
    r = client.post("/api/upload/init",
                    json={"filename": "a.mp4", "size": 3, "type": "video"})
    assert r.status_code == 401
