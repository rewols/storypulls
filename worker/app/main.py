import logging
import re
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app import pipeline
from app.models import Job
from app.urls import UnsupportedURL, parse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="StoryPulls worker")
# Whisper + ffmpeg are CPU-heavy; two concurrent jobs is plenty for a personal box.
_executor = ThreadPoolExecutor(max_workers=2)

MAX_UPLOAD_FILES = 12
MAX_UPLOAD_BYTES = 200 * 1024 * 1024


class UrlJobRequest(BaseModel):
    url: str
    refresh: bool = False


def _start(source: pipeline.Source, workdir, refresh: bool = False) -> Job:
    job = Job(id=uuid.uuid4().hex)
    pipeline.save_job(job)
    _executor.submit(pipeline.run, job, source, workdir, refresh)
    return job


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/jobs", response_model=Job)
def create_url_job(req: UrlJobRequest) -> Job:
    try:
        parsed = parse(req.url)
    except UnsupportedURL as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Couldn't open that link: {err}") from err
    return _start(parsed, pipeline.new_workdir(), req.refresh)


@app.post("/jobs/upload", response_model=Job)
async def create_upload_job(
    files: list[UploadFile] = File(...),
    caption: str = Form(""),
) -> Job:
    if not files or len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(status_code=400, detail=f"Upload between 1 and {MAX_UPLOAD_FILES} files.")
    workdir = pipeline.new_workdir()
    saved, total = [], 0
    for i, upload in enumerate(files):
        suffix = re.sub(r"[^.\w]", "", "." + (upload.filename or "file").rsplit(".", 1)[-1])[:8]
        dest = workdir / f"upload_{i:02d}{suffix}"
        data = await upload.read()
        total += len(data)
        if total > MAX_UPLOAD_BYTES:
            shutil.rmtree(workdir, ignore_errors=True)
            raise HTTPException(status_code=413, detail="Uploads are limited to 200 MB in total.")
        dest.write_bytes(data)
        saved.append(dest)
    return _start(pipeline.UploadSource(files=saved, caption=caption), workdir)


@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    job = pipeline.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job (the worker may have restarted).")
    return job
