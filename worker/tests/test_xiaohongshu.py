import pytest

from app.fetchers.base import FetchError
from app.fetchers.xiaohongshu import note_caption, note_image_urls, note_video_url, parse_initial_state
from conftest import FIXTURES

NOTE_ID = "6650a1b2000000001e01abcd"


@pytest.fixture
def note():
    return parse_initial_state((FIXTURES / "xhs_image_note.html").read_text(), NOTE_ID)


def test_parses_image_note(note):
    assert note["type"] == "normal"
    assert note["user"]["nickname"] == "咖啡探店小王"


def test_caption_strips_topic_markers(note):
    caption = note_caption(note)
    assert caption.startswith("台北大安区咖啡馆合集")
    assert "Simple Kaffa 興波咖啡" in caption
    assert "#台北咖啡 #大安区" in caption
    assert "[话题]" not in caption


def test_image_urls_prefer_default_and_fall_back_to_info_list(note):
    assert note_image_urls(note) == [
        "https://sns-webpic-qc.xhscdn.com/202405/abc/1040g001!nd_dft_wlteh_webp_3",
        "https://sns-webpic-qc.xhscdn.com/dft2",
    ]


def test_no_video_on_image_note(note):
    assert note_video_url(note) is None


def test_video_url_prefers_h264():
    note = {"video": {"media": {"stream": {
        "h265": [{"masterUrl": "https://v/h265.mp4"}],
        "h264": [{"masterUrl": "", "backupUrls": ["https://v/h264-backup.mp4"]}],
    }}}}
    assert note_video_url(note) == "https://v/h264-backup.mp4"


def test_login_wall_raises_helpful_error():
    with pytest.raises(FetchError, match="login wall"):
        parse_initial_state("<html><body>请登录</body></html>", NOTE_ID)


def test_missing_note_raises():
    html = '<script>window.__INITIAL_STATE__={"note":{"noteDetailMap":{}}}</script>'
    with pytest.raises(FetchError, match="Couldn't find the note"):
        parse_initial_state(html, NOTE_ID)
