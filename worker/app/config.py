import os
from dataclasses import dataclass, field
from pathlib import Path


def _path_or_none(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    return Path(value) if value else None


@dataclass(frozen=True)
class Settings:
    anthropic_model: str = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
    claude_effort: str = os.environ.get("CLAUDE_EFFORT", "medium")
    google_maps_api_key: str = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    whisper_model: str = os.environ.get("WHISPER_MODEL", "small")
    data_dir: Path = Path(os.environ.get("DATA_DIR", "./data"))
    max_frames: int = int(os.environ.get("MAX_FRAMES", "12"))
    max_video_seconds: int = int(os.environ.get("MAX_VIDEO_SECONDS", "600"))
    cookies: dict[str, Path | None] = field(
        default_factory=lambda: {
            "tiktok": _path_or_none("COOKIES_TIKTOK"),
            "instagram": _path_or_none("COOKIES_INSTAGRAM"),
            "xiaohongshu": _path_or_none("COOKIES_XIAOHONGSHU"),
        }
    )


settings = Settings()
