"""content_id 계산 (Phase 2.1).

파일을 경로/이름이 아니라 **내용 기반 부분 해시**로 식별한다.
`크기 + 앞 1MB 해시 + 뒤 1MB 해시` 조합 → 이름 변경·USB 내 이동에도 동일 id 유지.
파일이 2MB 이하이면 전체를 1회 해시한다.
"""
import hashlib
import os

_CHUNK = 1024 * 1024  # 1MB


def compute_content_id(path: str) -> str:
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size <= 2 * _CHUNK:
            head = f.read()
            tail = b""
        else:
            head = f.read(_CHUNK)
            f.seek(-_CHUNK, os.SEEK_END)
            tail = f.read(_CHUNK)
    h1 = hashlib.sha1(head).hexdigest()[:16]
    h2 = hashlib.sha1(tail).hexdigest()[:16]
    return f"{size}-{h1}-{h2}"
