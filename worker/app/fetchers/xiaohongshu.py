"""Xiaohongshu notes: parse window.__INITIAL_STATE__ from the page.

Handles both image notes (most XHS travel posts) and video notes. The page needs the
`xsec_token` query param that share links carry; pasting a bare /explore/<id> URL often
returns a login wall.
"""

import json
import re
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import httpx
from yt_dlp.utils import js_to_json

from app.config import settings
from app.fetchers.base import FetchError, FetchResult
from app.urls import ParsedURL

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
_STATE_RE = re.compile(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", re.S)
MAX_IMAGES = 12


def parse_initial_state(html: str, note_id: str) -> dict:
    """Return the note dict for `note_id`, or raise FetchError."""
    match = _STATE_RE.search(html)
    if not match:
        raise FetchError("Xiaohongshu returned a page without post data (login wall or captcha). "
                         "Try the full share link, set COOKIES_XIAOHONGSHU, or upload screenshots.")
    state = json.loads(js_to_json(match.group(1)))
    detail_map = (state.get("note") or {}).get("noteDetailMap") or {}
    note = (detail_map.get(note_id) or {}).get("note")
    if not note:
        # Some page variants key the map differently; fall back to the only entry.
        notes = [v.get("note") for v in detail_map.values() if isinstance(v, dict) and v.get("note")]
        note = notes[0] if len(notes) == 1 else None
    if not note:
        raise FetchError("Couldn't find the note in the Xiaohongshu page (deleted or private?).")
    return note


def note_image_urls(note: dict) -> list[str]:
    urls = []
    for image in note.get("imageList") or []:
        url = image.get("urlDefault") or image.get("urlPre") or image.get("url")
        if not url:
            infos = image.get("infoList") or []
            url = next((i.get("url") for i in infos if i.get("imageScene") == "WB_DFT"), None)
        if url:
            urls.append(url.replace("http://", "https://", 1))
    return urls[:MAX_IMAGES]


def note_video_url(note: dict) -> str | None:
    streams = ((note.get("video") or {}).get("media") or {}).get("stream") or {}
    # h264 first: decodes everywhere; h265/av1 as fallbacks.
    for codec in ("h264", "h265", "av1", "h266"):
        for stream in streams.get(codec) or []:
            if url := stream.get("masterUrl") or next(iter(stream.get("backupUrls") or []), None):
                return url
    return None


def note_caption(note: dict) -> str:
    title = (note.get("title") or "").strip()
    desc = (note.get("desc") or "").strip()
    # Hashtags render as "#广州[话题]#" — strip the marker, keep the tag text.
    desc = re.sub(r"\[话题\]#", "", desc)
    return "\n".join(part for part in (title, desc) if part)


def _client() -> httpx.Client:
    cookies = None
    if path := settings.cookies.get("xiaohongshu"):
        jar = MozillaCookieJar(str(path))
        jar.load(ignore_discard=True, ignore_expires=True)
        cookies = httpx.Cookies(jar)
    return httpx.Client(
        headers={"User-Agent": _UA, "Referer": "https://www.xiaohongshu.com/"},
        cookies=cookies,
        follow_redirects=True,
        timeout=30,
    )


def _download(client: httpx.Client, url: str, dest: Path) -> Path:
    with client.stream("GET", url) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_bytes():
                fh.write(chunk)
    return dest


def fetch_xiaohongshu(parsed: ParsedURL, workdir: Path) -> FetchResult:
    with _client() as client:
        try:
            page = client.get(parsed.url)
            page.raise_for_status()
        except httpx.HTTPError as err:
            raise FetchError(f"Couldn't load the Xiaohongshu page: {err}") from err

        note = parse_initial_state(page.text, parsed.post_id)
        result = FetchResult(
            platform="xiaohongshu",
            url=parsed.url,
            caption=note_caption(note),
            author=(note.get("user") or {}).get("nickname") or (note.get("user") or {}).get("nickName"),
        )

        try:
            if note.get("type") == "video" and (video_url := note_video_url(note)):
                result.video_paths.append(_download(client, video_url, workdir / f"{parsed.post_id}.mp4"))
            for i, url in enumerate(note_image_urls(note)):
                # Video notes carry a cover image; it's cheap context, keep just the first.
                if result.video_paths and i > 0:
                    break
                result.image_paths.append(_download(client, url, workdir / f"img_{i:02d}"))
        except httpx.HTTPError as err:
            raise FetchError(f"Xiaohongshu blocked the media download: {err}") from err

    return result
