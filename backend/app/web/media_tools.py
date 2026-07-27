# backend/app/web/media_tools.py
"""ffmpeg/ffprobe 래퍼: 미디어 길이 측정 · 썸네일 생성.

- ffprobe 로 duration(초) 조회.
- ffmpeg 로 지정 위치 프레임(또는 사진)을 축소해 jpg 썸네일 생성.
ffmpeg/ffprobe 는 PATH 에 있다고 가정(배포 대상 RPi5·개발 PC 모두 설치).
"""
from __future__ import annotations

import os
import subprocess

_THUMB_WIDTH = 320


def probe_duration(path: str) -> float | None:
    """미디어 길이를 초 단위로 반환. 실패(파일 없음·비미디어 등) 시 None."""
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None


def make_thumbnail(src: str, dst: str, at_sec: float = 1.0) -> bool:
    """src 의 at_sec 위치 프레임(사진이면 그 이미지)을 축소해 dst(jpg)로 저장.

    at_sec<=0 이면 -ss(탐색)를 생략한다 — 정지 이미지(사진)는 1초 탐색 시
    프레임을 못 뽑아 실패하므로 사진 썸네일은 at_sec=0 으로 호출해야 한다.
    성공 시 True, 실패 시 False.
    """
    cmd = ["ffmpeg", "-y"]
    if at_sec > 0:
        cmd += ["-ss", str(at_sec)]
    cmd += ["-i", src, "-frames:v", "1", "-vf", f"scale={_THUMB_WIDTH}:-1", dst]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return False
    return proc.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0
