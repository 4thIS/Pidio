#!/usr/bin/env python
"""개발용 샘플 미디어 생성 (USB 없이 앱 테스트).

ffmpeg 로 짧은 영상·음악·사진을 backend/sample_media/{videos,pictures,music} 에 만든다.
생성 후 서버를 아래처럼 띄우면 부팅 스캔으로 목록에 뜬다:

    # backend/ 에서 (PowerShell)
    $env:PIDIO_MEDIA_ROOT="sample_media"; $env:PIDIO_DB="dev.db"
    uv run uvicorn app.web.main:app --port 8000

    # bash
    PIDIO_MEDIA_ROOT=sample_media PIDIO_DB=dev.db uv run uvicorn app.web.main:app --port 8000

ffmpeg 이 PATH 에 있어야 한다(winget install Gyan.FFmpeg).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "sample_media"

# (상대경로, ffmpeg 입력 인자들)
SAMPLES = [
    ("videos/무지개_테스트.mp4",
     ["-f", "lavfi", "-i", "testsrc=duration=6:size=640x360:rate=24",
      "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
      "-pix_fmt", "yuv420p", "-shortest"]),
    ("videos/컬러바.mp4",
     ["-f", "lavfi", "-i", "smptebars=duration=4:size=640x360:rate=24", "-pix_fmt", "yuv420p"]),
    ("music/도음_8초.mp3", ["-f", "lavfi", "-i", "sine=frequency=523:duration=8"]),
    ("music/미음_5초.mp3", ["-f", "lavfi", "-i", "sine=frequency=659:duration=5"]),
    ("pictures/파랑.jpg", ["-f", "lavfi", "-i", "color=c=0x3a4a86:s=800x600", "-frames:v", "1"]),
    ("pictures/자주.jpg", ["-f", "lavfi", "-i", "color=c=0x7c3f6b:s=800x600", "-frames:v", "1"]),
    ("pictures/패턴.jpg", ["-f", "lavfi", "-i", "testsrc=size=800x600:rate=1", "-frames:v", "1"]),
]


def main() -> int:
    if shutil.which("ffmpeg") is None:
        print("ffmpeg 를 찾을 수 없습니다. 설치: winget install Gyan.FFmpeg", file=sys.stderr)
        return 1
    for sub in ("videos", "pictures", "music"):
        (ROOT / sub).mkdir(parents=True, exist_ok=True)
    for rel, args in SAMPLES:
        dst = ROOT / rel
        subprocess.run(["ffmpeg", "-y", *args, str(dst)], check=True, capture_output=True)
        print(f"  생성: {rel}")
    print(f"완료 → {ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
