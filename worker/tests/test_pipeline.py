"""Upload path end to end with real ffmpeg; Whisper and Claude are stubbed."""

import subprocess

import pytest

from app import pipeline
from app.config import Settings
from app.media import frame_times
from app.models import Extraction, Job
from app.transcribe import Transcript
from test_extract import SAMPLE


@pytest.mark.parametrize(
    ("duration", "max_frames", "expected_count"),
    [(0, 12, 1), (3, 12, 1), (20, 12, 5), (300, 12, 12)],
)
def test_frame_times(duration, max_frames, expected_count):
    times = frame_times(duration, max_frames)
    assert len(times) == expected_count
    assert all(0 <= t <= max(duration, 0) for t in times)


def make_video(path, seconds=8, audio=True):
    args = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=640x360:rate=10"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-shortest"]
    subprocess.run(args + [str(path)], check=True)
    return path


def make_image(path):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=1200x1600", "-frames:v", "1", str(path)],
        check=True,
    )
    return path


@pytest.fixture
def stubbed(monkeypatch, tmp_path):
    calls = {}

    def fake_transcribe(audio):
        calls["audio"] = audio
        return Transcript(language="ja", segments=[(4.0, "first stop is Ichiran in Shibuya")])

    def fake_extract(caption, transcript, frames, author):
        calls.update(caption=caption, transcript=transcript, frames=frames)
        return Extraction(places=SAMPLE.places, notes=None)

    monkeypatch.setattr(pipeline, "transcribe", fake_transcribe)
    monkeypatch.setattr(pipeline, "extract_places", fake_extract)
    # No Maps key -> places come back unverified with a search link, no network.
    monkeypatch.setattr("app.geocode.settings", Settings(google_maps_api_key=""))
    monkeypatch.setattr(pipeline.store, "put", lambda key, result: None)
    return calls


def test_upload_video_and_image(tmp_path, stubbed):
    workdir = tmp_path / "work"
    workdir.mkdir()
    video = make_video(workdir / "upload_00.mp4")
    image = make_image(workdir / "upload_01.png")

    job = Job(id="t1")
    pipeline.run(job, pipeline.UploadSource(files=[video, image], caption="Tokyo ramen run"), workdir)

    assert job.stage == "done", job.error
    assert job.result.source.kind == "video"
    assert job.result.transcript_language == "ja"
    assert job.result.places[0].name == "Ichiran Shibuya"
    assert job.result.places[0].maps_url.startswith("https://www.google.com/maps/search/")
    assert stubbed["transcript"] == "[0:04] first stop is Ichiran in Shibuya"
    labels = [f.label for f in stubbed["frames"]]
    assert labels[0] == "Post image 1"
    assert any(label.startswith("Video frame at") for label in labels)
    assert not workdir.exists(), "workdir should be cleaned up"


def test_failure_reports_stage(tmp_path, monkeypatch):
    def boom(*_):
        raise RuntimeError("nope")

    monkeypatch.setattr(pipeline, "fetch", boom)
    from app.urls import ParsedURL

    workdir = tmp_path / "w"
    workdir.mkdir()
    monkeypatch.setattr(pipeline.store, "get", lambda key: None)
    job = Job(id="t2")
    pipeline.run(job, ParsedURL("tiktok", "https://www.tiktok.com/@a/video/1", "1"), workdir)
    assert job.stage == "error"
    assert job.failed_stage == "fetching"
    assert job.error == "nope"
