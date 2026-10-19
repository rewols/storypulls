from dataclasses import dataclass, field
from pathlib import Path

from app.models import Platform


class FetchError(RuntimeError):
    """Raised when a platform refuses or we can't parse the post. Shown to the user."""


@dataclass
class FetchResult:
    platform: Platform
    url: str | None
    caption: str = ""
    author: str | None = None
    video_paths: list[Path] = field(default_factory=list)
    image_paths: list[Path] = field(default_factory=list)

    @property
    def kind(self) -> str:
        if self.video_paths:
            return "video"
        return "images" if self.image_paths else "text"
