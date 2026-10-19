"""Turn whatever the user pasted into (platform, fetchable URL, cache key)."""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.models import Platform

# Share sheets (esp. XHS) paste "title... http://xhslink.com/a/xyz 复制本条信息..." — grab the URL.
_URL_RE = re.compile(r"https?://[^\s　-〿＀-￯]+")

_SHORT_HOSTS = {"vm.tiktok.com", "vt.tiktok.com", "xhslink.com", "www.xhslink.com"}

_PATTERNS: list[tuple[Platform, re.Pattern[str]]] = [
    ("tiktok", re.compile(r"tiktok\.com/(?:@[\w.\-]+/)?(?:video|photo)/(\d+)")),
    ("tiktok", re.compile(r"tiktok\.com/t/(\w+)")),
    ("instagram", re.compile(r"instagram\.com/(?:[\w.]+/)?(?:reels?|p|tv)/([\w\-]+)")),
    ("xiaohongshu", re.compile(r"xiaohongshu\.com/(?:explore|discovery/item|user/profile/\w+)/([0-9a-f]{24})")),
]


class UnsupportedURL(ValueError):
    pass


@dataclass(frozen=True)
class ParsedURL:
    platform: Platform
    url: str  # URL to fetch (keeps query params such as XHS's xsec_token)
    post_id: str

    @property
    def cache_key(self) -> str:
        return f"{self.platform}:{self.post_id}"


def extract_url(text: str) -> str:
    match = _URL_RE.search(text.strip())
    if not match:
        raise UnsupportedURL("No link found in the pasted text.")
    return match.group(0).rstrip(".,!?)\"'")


def match_platform(url: str) -> ParsedURL | None:
    for platform, pattern in _PATTERNS:
        if m := pattern.search(url):
            return ParsedURL(platform=platform, url=url, post_id=m.group(1))
    return None


def _resolve_redirect(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"}
    with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as client:
        return str(client.get(url).url)


def parse(text: str, resolve=_resolve_redirect) -> ParsedURL:
    url = extract_url(text)
    host = (urlparse(url).hostname or "").lower()
    if host in _SHORT_HOSTS or (host.endswith("tiktok.com") and "/t/" in url):
        url = resolve(url)
    parsed = match_platform(url)
    if not parsed:
        raise UnsupportedURL("That doesn't look like a TikTok, Instagram or Xiaohongshu post link.")
    return parsed
