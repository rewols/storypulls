from types import SimpleNamespace

import pytest

from app import extract
from app.extract import ExtractionError, build_content, extract_places
from app.media import Frame
from app.models import Extraction

SAMPLE = Extraction.model_validate({
    "places": [{
        "name": "Ichiran Shibuya",
        "name_local": "一蘭 渋谷店",
        "category": "restaurant",
        "address_hint": "Jinnan 1-22-7",
        "city": "Tokyo",
        "country": "Japan",
        "description": "Solo-booth tonkotsu ramen; go after 11pm to skip the queue.",
        "evidence": [
            {"source": "audio", "detail": "first stop is Ichiran in Shibuya", "timestamp": "0:04"},
            {"source": "frame", "detail": "sign reading 一蘭", "timestamp": "0:06"},
        ],
        "confidence": "high",
    }],
    "notes": None,
})


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def fake_client(response):
    messages = FakeMessages(response)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


@pytest.fixture
def frame(tmp_path):
    path = tmp_path / "f.jpg"
    path.write_bytes(b"\xff\xd8\xff\xd9")
    return Frame(path, 6.0, "Video frame at 0:06")


def test_build_content_labels_each_image_then_text(frame):
    content = build_content("caption!", "[0:04] hello", [frame], "@me")
    assert [b["type"] for b in content] == ["text", "image", "text"]
    assert content[0]["text"] == "Video frame at 0:06"
    assert content[1]["source"]["media_type"] == "image/jpeg"
    assert "<caption>\ncaption!\n</caption>" in content[2]["text"]
    assert "[0:04] hello" in content[2]["text"]


def test_extract_places_sends_structured_request(frame):
    client, messages = fake_client(SimpleNamespace(stop_reason="end_turn", parsed_output=SAMPLE))
    result = extract_places("cap", "[0:04] hi", [frame], "@me", client=client)
    assert result.places[0].name_local == "一蘭 渋谷店"
    call = messages.calls[0]
    assert call["output_format"] is Extraction
    assert call["system"] == extract.SYSTEM_PROMPT
    assert call["fallbacks"] == "default"
    assert "tool_choice" not in call


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_extract_places_raises_on_bad_stop(frame, stop_reason):
    client, _ = fake_client(SimpleNamespace(stop_reason=stop_reason, parsed_output=None))
    with pytest.raises(ExtractionError):
        extract_places("cap", "", [frame], client=client)


def test_schema_round_trips_without_optional_fields():
    minimal = Extraction.model_validate({"places": [{
        "name": "Fushimi Inari", "category": "attraction",
        "description": "Torii gates.", "evidence": [{"source": "caption", "detail": "Fushimi Inari"}],
        "confidence": "high",
    }]})
    assert minimal.places[0].name_local is None
