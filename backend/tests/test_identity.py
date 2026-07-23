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


_CHUNK = 1024 * 1024  # 구현과 동일한 청크 크기(경계 테스트용)


def test_empty_file(tmp_path):
    # size 0 파일도 예외 없이 처리되고, 두 빈 파일은 같은 id
    a = _write(tmp_path, "e1.bin", b"")
    b = _write(tmp_path, "e2.bin", b"")
    assert compute_content_id(a)  # 값 반환(예외 없음)
    assert compute_content_id(a) == compute_content_id(b)


def test_two_mb_boundary_is_deterministic(tmp_path):
    # 정확히 2MB(전체해시 분기)와 2MB+1(앞뒤 분기) 모두 오류 없이·결정적으로 동작
    exact = _write(tmp_path, "exact.bin", b"Q" * (2 * _CHUNK))
    over = _write(tmp_path, "over.bin", b"Q" * (2 * _CHUNK + 1))
    assert compute_content_id(exact) == compute_content_id(exact)  # 결정적
    assert compute_content_id(over) == compute_content_id(over)
    # 크기가 다르므로 id도 달라야 함
    assert compute_content_id(exact) != compute_content_id(over)
