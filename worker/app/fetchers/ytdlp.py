"""TikTok and Instagram (and XHS video notes) via yt-dlp."""

from pathlib import Path

import yt_dlp

from app.config import settings
from app.fetchers.base import FetchError, FetchResult
from app.urls import ParsedURL


def _ydl_opts(platform: str, workdir: Path) -> dict:
    opts = {
        "outtmpl": str(workdir / "%(id)s.%(ext)s"),
        # 720p is plenty for reading on-screen text and keeps downloads small.
        "format": "bv*[height<=720]+ba/b[height<=720]/bv*+ba/b",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        "match_filter": yt_dlp.utils.match_filter_func(f"duration <=? {settings.max_video_seconds}"),
    }
    if cookie := settings.cookies.get(platform):
        opts["cookiefile"] = str(cookie)
    return opts


def _downloaded_files(info: dict) -> list[Path]:
    entries = info.get("entries") or [info]
    paths: list[Path] = []
    for entry in entries:
        if not entry:
            continue
        for download in entry.get("requested_downloads") or []:
            if fp := download.get("filepath"):
                paths.append(Path(fp))
    return [p for p in paths if p.exists()]


def _friendly(platform: str, err: Exception) -> str:
    msg = str(err)
    if platform == "instagram" and ("login" in msg.lower() or "rate" in msg.lower()):
        return "Instagram wants a login for this post. Set COOKIES_INSTAGRAM, or upload the video instead."
    if "There is no video" in msg or "No video formats" in msg:
        return "This post has no video (probably a photo carousel). Upload screenshots instead."
    return f"Couldn't download from {platform}: {msg.splitlines()[0][:200]}"


def fetch_with_ytdlp(parsed: ParsedURL, workdir: Path) -> FetchResult:
    try:
        with yt_dlp.YoutubeDL(_ydl_opts(parsed.platform, workdir)) as ydl:
            info = ydl.extract_info(parsed.url, download=True)
    except yt_dlp.utils.DownloadError as err:
        raise FetchError(_friendly(parsed.platform, err)) from err

    if not info:
        raise FetchError("The post was skipped (longer than MAX_VIDEO_SECONDS?).")

    first = (info.get("entries") or [info])[0] or {}
    caption = info.get("description") or first.get("description") or info.get("title") or ""
    return FetchResult(
        platform=parsed.platform,
        url=parsed.url,
        caption=caption.strip(),
        author=info.get("uploader") or first.get("uploader") or info.get("channel"),
        video_paths=_downloaded_files(info),
    )
