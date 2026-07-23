# backend/tests/test_media_tools.py
"""Task 7.1 미디어 처리(ffmpeg 래퍼) 테스트.

ffmpeg/ffprobe 가 없으면 전체 skip (계획 7.1 규정).
"""
import shutil
import subprocess

import pytest

from app.web import media_tools

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe 미설치",
)


@pytest.fixture
def sample_video(tmp_path):
    """ffmpeg lavfi 로 1초짜리 테스트 영상 생성."""
    dst = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=1:size=320x240:rate=25",
            "-pix_fmt", "yuv420p",
            str(dst),
        ],
        check=True,
        capture_output=True,
    )
    return str(dst)


def test_probe_duration_returns_seconds(sample_video):
    dur = media_tools.probe_duration(sample_video)
    assert dur is not None
    assert abs(dur - 1.0) < 0.3


def test_probe_duration_missing_file_returns_none(tmp_path):
    assert media_tools.probe_duration(str(tmp_path / "nope.mp4")) is None


def test_make_thumbnail_creates_jpg(sample_video, tmp_path):
    dst = tmp_path / "thumb.jpg"
    ok = media_tools.make_thumbnail(sample_video, str(dst), at_sec=0.5)
    assert ok is True
    assert dst.exists() and dst.stat().st_size > 0


def test_make_thumbnail_bad_source_returns_false(tmp_path):
    dst = tmp_path / "thumb.jpg"
    ok = media_tools.make_thumbnail(str(tmp_path / "nope.mp4"), str(dst))
    assert ok is False
