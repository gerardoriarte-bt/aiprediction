"""
Video preprocessing for R6 creative tests.

Given a video file, extract a small set of evenly-spaced frames (so the
vision model sees the narrative arc without paying for every frame) and
transcribe the audio track via Whisper. Both steps are best-effort —
when ffmpeg or Whisper are unavailable, callers get an empty result and
the variant is treated as text-only.

Two binary dependencies:
- ffmpeg (system) — for frame and audio extraction.
- OpenAI Whisper API — used through the existing OpenAI client. Whisper
  charges $0.006/min so even a 60s video is fractions of a cent.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from ...config import Config
from ...utils.logger import get_logger


logger = get_logger("mirofish.creative_testing.video")

# Cap the number of frames we send to the LLM. 8 keeps the per-test cost
# bounded ($0.05–0.20 incremental at high detail) while still capturing
# the typical 6-15s ad arc.
DEFAULT_MAX_FRAMES = 8

# Cap audio length sent to Whisper. Most ad creatives are <60s; a hard cap
# at 300s avoids surprise bills if a marketer uploads a long-form clip.
MAX_AUDIO_SECONDS = 300


@dataclass
class VideoExtraction:
    frame_paths: List[str]
    audio_transcript: Optional[str]
    duration_seconds: Optional[float]


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _probe_duration_seconds(video_path: str) -> Optional[float]:
    if not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                video_path,
            ],
            stderr=subprocess.PIPE,
            timeout=10,
        )
        data = json.loads(out.decode("utf-8") or "{}")
        return float(data.get("format", {}).get("duration") or 0) or None
    except (subprocess.SubprocessError, ValueError, OSError) as e:
        logger.warning(f"ffprobe failed on {video_path}: {e}")
        return None


def _extract_frames(video_path: str, out_dir: str, max_frames: int) -> List[str]:
    """Pull `max_frames` evenly-spaced JPEG frames from the video."""
    if not _ffmpeg_available():
        return []
    duration = _probe_duration_seconds(video_path) or 0
    # If duration is unknown or short, fall back to fixed cadence (1 fps).
    if duration <= 0:
        fps_filter = "1"
    else:
        # Spread frames across the duration; e.g. 8 frames over 24s -> 1 every 3s.
        step = max(1.0, duration / max_frames)
        fps_filter = f"1/{step:.3f}"

    pattern = os.path.join(out_dir, "frame_%02d.jpg")
    try:
        subprocess.check_call(
            [
                "ffmpeg",
                "-loglevel", "error",
                "-i", video_path,
                "-vf", f"fps={fps_filter},scale='min(1024,iw)':-2",
                "-frames:v", str(max_frames),
                "-q:v", "3",
                pattern,
            ],
            timeout=120,
        )
    except subprocess.SubprocessError as e:
        logger.warning(f"ffmpeg frame extraction failed: {e}")
        return []

    return sorted(
        os.path.join(out_dir, name)
        for name in os.listdir(out_dir)
        if name.startswith("frame_") and name.endswith(".jpg")
    )


def _extract_audio(video_path: str, out_dir: str) -> Optional[str]:
    """Drop the audio track to mp3 (mono, 16kHz) for Whisper."""
    if not _ffmpeg_available():
        return None
    audio_path = os.path.join(out_dir, "audio.mp3")
    try:
        subprocess.check_call(
            [
                "ffmpeg",
                "-loglevel", "error",
                "-i", video_path,
                "-t", str(MAX_AUDIO_SECONDS),
                "-ac", "1",
                "-ar", "16000",
                "-vn",
                "-q:a", "5",
                audio_path,
            ],
            timeout=120,
        )
    except subprocess.SubprocessError as e:
        logger.info(f"audio extraction skipped (no audio track or ffmpeg failed): {e}")
        return None
    if not os.path.isfile(audio_path) or os.path.getsize(audio_path) < 256:
        return None
    return audio_path


def _whisper_transcribe(audio_path: str) -> Optional[str]:
    """Best-effort Whisper transcription. Returns None on any failure."""
    if not Config.LLM_API_KEY:
        logger.info("Whisper skipped: LLM_API_KEY not set.")
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
        with open(audio_path, "rb") as fh:
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=fh,
                response_format="text",
            )
        text = resp if isinstance(resp, str) else getattr(resp, "text", "")
        text = (text or "").strip()
        return text or None
    except Exception as e:
        logger.warning(f"Whisper transcription failed: {e}")
        return None


def extract(video_path: str, work_dir: str, max_frames: int = DEFAULT_MAX_FRAMES) -> VideoExtraction:
    """Extract frames + transcript for one video.

    Caller passes a `work_dir` that we own — frames go into it directly so
    the API endpoint can hand each path to the existing slide pipeline.
    """
    os.makedirs(work_dir, exist_ok=True)
    duration = _probe_duration_seconds(video_path)
    frames = _extract_frames(video_path, work_dir, max_frames)
    transcript = None
    audio_path = _extract_audio(video_path, work_dir)
    if audio_path:
        transcript = _whisper_transcribe(audio_path)
        # Audio file is no longer needed after transcription; keep the dir
        # tidy so the API only serves the frames as static assets.
        try:
            os.remove(audio_path)
        except OSError:
            pass
    return VideoExtraction(
        frame_paths=frames,
        audio_transcript=transcript,
        duration_seconds=duration,
    )
