import os

from app.domain.identity import compute_content_id


def _write(tmp_path, name, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


def test_same_content_same_id_even_after_rename(tmp_path):
    data = b"A" * (3 * 1024 * 1024)  # 3MB
    a = _write(tmp_path, "a.bin", data)
    id1 = compute_content_id(a)
    os.rename(a, str(tmp_path / "renamed.bin"))
    id2 = compute_content_id(str(tmp_path / "renamed.bin"))
    assert id1 == id2


def test_different_content_different_id(tmp_path):
    a = _write(tmp_path, "a.bin", b"A" * (3 * 1024 * 1024))
    b = _write(tmp_path, "b.bin", b"B" * (3 * 1024 * 1024))
    assert compute_content_id(a) != compute_content_id(b)


def test_same_size_different_edges_different_id(tmp_path):
    # 같은 크기지만 앞/뒤 내용이 다르면 다른 id (부분해시 검증)
    base = bytearray(b"X" * (3 * 1024 * 1024))
    a = _write(tmp_path, "a.bin", bytes(base))
    base[0] = ord("Y")
    base[-1] = ord("Z")
    b = _write(tmp_path, "b.bin", bytes(base))
    assert compute_content_id(a) != compute_content_id(b)


def test_small_file_under_2mb(tmp_path):
    a = _write(tmp_path, "s.bin", b"hello")
    assert compute_content_id(a)  # 예외 없이 값 반환
