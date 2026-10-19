"""ffmpeg helpers: audio for Whisper, sampled frames and normalised images for Claude."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

FRAME_WIDTH = 768


@dataclass
class Frame:
    path: Path
    timestamp: float | None  # None for still images
    label: str


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, capture_output=True, text=True)


def probe(video: Path) -> tuple[float, bool]:
    """Return (duration_seconds, has_audio)."""
    out = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
        "-of", "json", str(video),
    ]).stdout
    data = json.loads(out)
    duration = float((data.get("format") or {}).get("duration") or 0)
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams") or [])
    return duration, has_audio


def extract_audio(video: Path, dest: Path) -> Path:
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(dest)])
    return dest


def frame_times(duration: float, max_frames: int) -> list[float]:
    """Evenly spaced, roughly one frame per 4s, avoiding the very first/last instant."""
    if duration <= 0:
        return [0.0]
    count = max(1, min(max_frames, round(duration / 4)))
    step = duration / count
    return [round(step * (i + 0.5), 2) for i in range(count)]


def fmt_ts(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def sample_frames(video: Path, outdir: Path, max_frames: int, prefix: str = "") -> list[Frame]:
    duration, _ = probe(video)
    frames = []
    for i, ts in enumerate(frame_times(duration, max_frames)):
        dest = outdir / f"{prefix}frame_{i:02d}.jpg"
        _run([
            "ffmpeg", "-y", "-v", "error", "-ss", str(ts), "-i", str(video), "-frames:v", "1",
            "-vf", f"scale='min({FRAME_WIDTH},iw)':-2", "-q:v", "4", str(dest),
        ])
        if dest.exists():
            frames.append(Frame(dest, ts, f"Video frame at {fmt_ts(ts)}"))
    return frames


def normalise_image(src: Path, dest: Path) -> Path:
    """Convert any image (webp/heic-as-jpeg/png) to a downscaled JPEG Claude accepts."""
    _run([
        "ffmpeg", "-y", "-v", "error", "-i", str(src), "-frames:v", "1",
        "-vf", f"scale='min({FRAME_WIDTH * 2},iw)':-2", "-q:v", "4", str(dest),
    ])
    return dest
