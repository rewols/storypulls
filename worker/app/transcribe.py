import threading
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.media import fmt_ts

_model = None
_lock = threading.Lock()


@dataclass
class Transcript:
    language: str | None
    segments: list[tuple[float, str]]

    def render(self) -> str:
        return "\n".join(f"[{fmt_ts(start)}] {text.strip()}" for start, text in self.segments)


def _get_model():
    global _model
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel

            # First call downloads the model (~500MB for "small") into the HF cache.
            _model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
    return _model


def transcribe(audio: Path) -> Transcript:
    segments, info = _get_model().transcribe(str(audio), vad_filter=True, beam_size=5)
    return Transcript(
        language=info.language,
        segments=[(s.start, s.text) for s in segments if s.text.strip()],
    )
