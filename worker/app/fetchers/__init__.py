from pathlib import Path

from app.fetchers.base import FetchError, FetchResult
from app.urls import ParsedURL


def fetch(parsed: ParsedURL, workdir: Path) -> FetchResult:
    if parsed.platform == "xiaohongshu":
        from app.fetchers.xiaohongshu import fetch_xiaohongshu

        return fetch_xiaohongshu(parsed, workdir)

    from app.fetchers.ytdlp import fetch_with_ytdlp

    return fetch_with_ytdlp(parsed, workdir)


__all__ = ["fetch", "FetchError", "FetchResult"]
