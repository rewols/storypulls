"""One Claude call: caption + transcript + frames -> structured list of places."""

import base64

import anthropic

from app.config import settings
from app.media import Frame
from app.models import Extraction

SYSTEM_PROMPT = """\
You extract the real-world places featured in a social media post (Instagram Reel, TikTok, \
or Xiaohongshu note) so the viewer can find and visit them.

You get the post's caption, a timestamped transcript of its audio (may be empty, may be in \
any language, may contain speech-recognition errors), and images: frames sampled from the \
video and/or the post's photos.

Include a place only if it is a specific, visitable venue or spot: a restaurant, cafe, bar, \
shop, hotel, museum, viewpoint, park, beach, market, or a small named neighbourhood the post \
recommends visiting. Do not include cities, countries or regions on their own (use them to \
fill `city`/`country` instead), the creator's home, chains mentioned in passing, or generic \
things like "a ramen shop" with no name or identifying signage.

Use every source. Names often appear only on screen (text overlays, shop signs, menus, \
receipts, map screenshots) or only in the voiceover. If the same place shows up in several \
sources, merge it into one entry and list each piece of evidence. Correct obvious \
transcription errors when the frames or caption make the real name clear.

For places with a name in a non-Latin script, put the original in `name_local` exactly as \
written and put the English or romanised name in `name` (use the original again if there is \
no established English name). Copy address fragments, street names, districts, and nearby \
landmarks into `address_hint`; they are used to look the place up on Google Maps.

Confidence: high = named explicitly; medium = named but partly unclear, or identified from \
signage alone; low = inferred. Keep the places in the order the post presents them. If the \
post features no specific places, return an empty list and say why in `notes`.\
"""


def _image_block(frame: Frame) -> dict:
    data = base64.standard_b64encode(frame.path.read_bytes()).decode("ascii")
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}


def build_content(caption: str, transcript: str, frames: list[Frame], author: str | None) -> list[dict]:
    content: list[dict] = []
    for frame in frames:
        content.append({"type": "text", "text": frame.label})
        content.append(_image_block(frame))
    content.append({
        "type": "text",
        "text": (
            f"<author>{author or 'unknown'}</author>\n"
            f"<caption>\n{caption or '(no caption)'}\n</caption>\n"
            f"<transcript>\n{transcript or '(no speech)'}\n</transcript>\n\n"
            "List the places featured in this post."
        ),
    })
    return content


class ExtractionError(RuntimeError):
    pass


def extract_places(
    caption: str,
    transcript: str,
    frames: list[Frame],
    author: str | None = None,
    client: anthropic.Anthropic | None = None,
) -> Extraction:
    client = client or anthropic.Anthropic()
    try:
        response = client.beta.messages.parse(
            model=settings.anthropic_model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_content(caption, transcript, frames, author)}],
            output_format=Extraction,
            output_config={"effort": settings.claude_effort},
            # If a safety classifier declines, the API retries on a fallback model in the same call.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.RateLimitError as err:
        raise ExtractionError("Claude is rate-limiting us; try again in a minute.") from err
    except anthropic.APIStatusError as err:
        raise ExtractionError(f"Claude API error ({err.status_code}): {err.message}") from err
    except anthropic.APIConnectionError as err:
        raise ExtractionError("Couldn't reach the Claude API.") from err

    if response.stop_reason == "refusal":
        raise ExtractionError("Claude declined to analyse this post.")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise ExtractionError("Claude's answer was cut off or unparseable; try again.")
    return response.parsed_output
