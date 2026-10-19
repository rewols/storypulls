import pytest

from app.urls import UnsupportedURL, parse


def no_resolve(url):
    raise AssertionError(f"should not resolve {url}")


@pytest.mark.parametrize(
    ("text", "platform", "post_id"),
    [
        ("https://www.tiktok.com/@foodie.tokyo/video/7301234567890123456?is_from_webapp=1", "tiktok", "7301234567890123456"),
        ("https://www.tiktok.com/@a.b/photo/7301234567890123457", "tiktok", "7301234567890123457"),
        ("https://www.instagram.com/reel/C9xYz-AbCdE/?igsh=abc", "instagram", "C9xYz-AbCdE"),
        ("https://www.instagram.com/reels/C9xYz_AbCdE/", "instagram", "C9xYz_AbCdE"),
        ("https://instagram.com/p/C1abcDEF123/", "instagram", "C1abcDEF123"),
        ("https://www.instagram.com/someuser/reel/C9xYzAbCdE1/", "instagram", "C9xYzAbCdE1"),
        (
            "https://www.xiaohongshu.com/explore/6411cf99000000001300b6d9?xsec_token=ABC=&xsec_source=pc_feed",
            "xiaohongshu",
            "6411cf99000000001300b6d9",
        ),
        ("https://www.xiaohongshu.com/discovery/item/674051740000000007027a15", "xiaohongshu", "674051740000000007027a15"),
    ],
)
def test_parse_direct_links(text, platform, post_id):
    parsed = parse(text, resolve=no_resolve)
    assert (parsed.platform, parsed.post_id) == (platform, post_id)
    assert parsed.cache_key == f"{platform}:{post_id}"


def test_xhs_share_text_with_short_link_is_resolved_and_keeps_token():
    share = "东京必吃的5家拉面🍜 http://xhslink.com/a/AbCdEf123，复制本条信息，打开【小红书】App查看精彩内容！"
    target = "https://www.xiaohongshu.com/discovery/item/6411cf99000000001300b6d9?xsec_token=XYZ"
    seen = []

    def resolve(url):
        seen.append(url)
        return target

    parsed = parse(share, resolve=resolve)
    assert seen == ["http://xhslink.com/a/AbCdEf123"]
    assert parsed.platform == "xiaohongshu"
    assert parsed.url == target


def test_tiktok_short_link_is_resolved():
    parsed = parse(
        "https://vm.tiktok.com/ZMabc123/",
        resolve=lambda u: "https://www.tiktok.com/@x/video/7300000000000000001",
    )
    assert parsed.post_id == "7300000000000000001"


@pytest.mark.parametrize("text", ["no link here", "https://youtube.com/watch?v=abc", "https://www.instagram.com/someuser/"])
def test_rejects_unsupported(text):
    with pytest.raises(UnsupportedURL):
        parse(text, resolve=no_resolve)
