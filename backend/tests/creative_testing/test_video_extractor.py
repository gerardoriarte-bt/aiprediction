"""
Tests for video_extractor.

We generate the fixture mp4 on the fly with ffmpeg's `lavfi` testsrc filter
so we don't ship a binary asset. Tests are skipped automatically when
ffmpeg is not on PATH (CI environments may lack it).
"""

import os
import shutil
import subprocess
import tempfile

import pytest

from app.services.creative_testing import video_extractor as ve


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not on PATH",
)


def _make_silent_mp4(path, duration=6, fps=24, size="320x240"):
    subprocess.check_call([
        "ffmpeg", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration}:size={size}:rate={fps}",
        path,
    ])


def _make_video_with_audio(path, duration=4):
    """testsrc + sine wave for a video with a real audio track."""
    subprocess.check_call([
        "ffmpeg", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration}:size=320x240:rate=24",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-shortest",
        path,
    ])


def test_extract_silent_video_yields_frames_no_transcript(tmp_path):
    src = tmp_path / "silent.mp4"
    _make_silent_mp4(str(src))
    work = tmp_path / "work"

    result = ve.extract(str(src), str(work), max_frames=4)

    # 4 frames came out, evenly spaced.
    assert len(result.frame_paths) == 4
    for p in result.frame_paths:
        assert os.path.isfile(p)
        assert os.path.getsize(p) > 200  # not an empty file
    # Silent source -> no transcript.
    assert result.audio_transcript is None
    # Probe duration matches our 6s source within tolerance.
    assert result.duration_seconds is not None
    assert abs(result.duration_seconds - 6.0) < 0.5


def test_extract_caps_max_frames(tmp_path):
    src = tmp_path / "long.mp4"
    _make_silent_mp4(str(src), duration=20)
    work = tmp_path / "work"

    result = ve.extract(str(src), str(work), max_frames=3)
    assert len(result.frame_paths) <= 3


def test_extract_skips_transcript_when_no_api_key(tmp_path, monkeypatch):
    """Even with an audio track, if LLM_API_KEY is missing we skip Whisper
    and return a None transcript — the rest of the pipeline must still
    produce frames."""
    from app.config import Config
    monkeypatch.setattr(Config, "LLM_API_KEY", "")

    src = tmp_path / "with_audio.mp4"
    _make_video_with_audio(str(src))
    work = tmp_path / "work"

    result = ve.extract(str(src), str(work), max_frames=3)
    assert len(result.frame_paths) >= 1
    assert result.audio_transcript is None


def test_probe_duration_unknown_returns_none(tmp_path):
    """If ffprobe fails (e.g. missing file), the helper falls through."""
    bogus = tmp_path / "does_not_exist.mp4"
    assert ve._probe_duration_seconds(str(bogus)) is None


def test_extract_when_ffmpeg_missing(tmp_path, monkeypatch):
    """Patch _ffmpeg_available to False — extract must return an empty
    result instead of crashing."""
    monkeypatch.setattr(ve, "_ffmpeg_available", lambda: False)
    src = tmp_path / "x.mp4"
    src.write_bytes(b"not a real video")
    result = ve.extract(str(src), str(tmp_path / "work"), max_frames=4)
    assert result.frame_paths == []
    assert result.audio_transcript is None
