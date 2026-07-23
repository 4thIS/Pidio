"""USB 라이브러리 스캐너 (Phase 2.4).

USB의 videos/pictures/music 폴더를 훑어 미디어를 타입별로 upsert 하고,
이번 스캔에 존재하는 집합만 available=1 로 표시한다(파일시스템=진실).
neither mpv nor 길이/썸네일은 여기서 다루지 않는다(웹의 백그라운드 처리 몫).
"""
import os

from . import media_repo as mr
from .identity import compute_content_id

VIDEO_EXT = {".mp4", ".mkv", ".mov", ".avi", ".m4v", ".webm"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
MUSIC_EXT = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg"}

_FOLDERS = {
    "videos": ("video", VIDEO_EXT),
    "pictures": ("photo", PHOTO_EXT),
    "music": ("music", MUSIC_EXT),
}


def scan_library(conn, usb_root, id_fn=compute_content_id) -> dict:
    seen: set[str] = set()
    added: list[str] = []
    for folder, (mtype, exts) in _FOLDERS.items():
        base = os.path.join(usb_root, folder)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                if os.path.splitext(name)[1].lower() not in exts:
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, usb_root).replace("\\", "/")
                cid = id_fn(full)
                existed = mr.get_media(conn, cid) is not None
                mr.upsert_media(conn, cid, mtype, name, rel)
                seen.add(cid)
                if not existed:
                    added.append(cid)
    mr.set_available(conn, seen)
    return {"added": added, "seen": len(seen)}
