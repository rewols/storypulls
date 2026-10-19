"""Glue: source -> fetch -> transcript + frames -> Claude -> geocode -> Result."""

import logging
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app import store
from app.config import settings
from app.extract import extract_places
from app.fetchers import FetchResult, fetch
from app.geocode import geocode_all
from app.media import Frame, extract_audio, normalise_image, probe, sample_frames
from app.models import Job, Result, SourceInfo, Stage
from app.transcribe import Transcript, transcribe
from app.urls import ParsedURL

log = logging.getLogger(__name__)

_jobs: dict[str, Job] = {}
_jobs_lock = threading.Lock()


def get_job(job_id: str) -> Job | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def save_job(job: Job) -> None:
    with _jobs_lock:
        _jobs[job.id] = job


@dataclass
class UploadSource:
    files: list[Path]  # already saved into workdir
    caption: str = ""


Source = ParsedURL | UploadSource


def _from_upload(upload: UploadSource) -> FetchResult:
    result = FetchResult(platform="upload", url=None, caption=upload.caption.strip())
    for path in upload.files:
        try:
            _, has_audio = probe(path)
            is_video = has_audio or path.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
        except Exception:
            is_video = False
        (result.video_paths if is_video else result.image_paths).append(path)
    return result


def _transcribe_all(fetched: FetchResult, workdir: Path) -> Transcript:
    language, segments = None, []
    for i, video in enumerate(fetched.video_paths):
        _, has_audio = probe(video)
        if not has_audio:
            continue
        t = transcribe(extract_audio(video, workdir / f"audio_{i}.wav"))
        language = language or t.language
        segments.extend(t.segments)
    return Transcript(language=language, segments=segments)


def _collect_frames(fetched: FetchResult, workdir: Path) -> list[Frame]:
    frames: list[Frame] = []
    budget = settings.max_frames
    for i, path in enumerate(fetched.image_paths[:budget]):
        jpg = normalise_image(path, workdir / f"image_{i:02d}.jpg")
        frames.append(Frame(jpg, None, f"Post image {i + 1}"))
    remaining = max(0, budget - len(frames))
    videos = fetched.video_paths
    for i, video in enumerate(videos):
        share = remaining // len(videos) if remaining else 0
        if share:
            frames.extend(sample_frames(video, workdir, share, prefix=f"v{i}_"))
    return frames


def run(job: Job, source: Source, workdir: Path, refresh: bool = False) -> None:
    def stage(name: Stage) -> None:
        job.stage = name
        save_job(job)

    cache_key = source.cache_key if isinstance(source, ParsedURL) else None
    current: Stage = "fetching"
    try:
        if cache_key and not refresh and (cached := store.get(cache_key)):
            job.result, job.cached = cached, True
            stage("done")
            return

        stage(current := "fetching")
        fetched = fetch(source, workdir) if isinstance(source, ParsedURL) else _from_upload(source)
        if not (fetched.caption or fetched.video_paths or fetched.image_paths):
            raise RuntimeError("The post had no caption, video or images to analyse.")

        stage(current := "transcribing")
        transcript = _transcribe_all(fetched, workdir)
        frames = _collect_frames(fetched, workdir)

        stage(current := "analysing")
        extraction = extract_places(fetched.caption, transcript.render(), frames, fetched.author)

        stage(current := "geocoding")
        places = geocode_all(extraction.places)

        job.result = Result(
            source=SourceInfo(
                platform=fetched.platform, url=fetched.url, author=fetched.author,
                caption=fetched.caption, kind=fetched.kind,
            ),
            transcript_language=transcript.language,
            places=places,
            notes=extraction.notes,
        )
        if cache_key:
            store.put(cache_key, job.result)
        stage("done")
    except Exception as err:  # surfaced to the UI, so keep the message human
        log.exception("job %s failed during %s", job.id, current)
        job.error = str(err) or err.__class__.__name__
        job.failed_stage = current
        stage("error")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def new_workdir() -> Path:
    return Path(tempfile.mkdtemp(prefix="storypulls_"))
