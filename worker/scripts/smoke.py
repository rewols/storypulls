"""Run the whole pipeline on one link and print the places.

    python -m scripts.smoke "https://www.tiktok.com/@user/video/123"
    python -m scripts.smoke --fetch-only "<url>"   # just check the download works
"""

import argparse
import json
import sys

from app import pipeline
from app.fetchers import fetch
from app.models import Job
from app.urls import parse


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--fetch-only", action="store_true")
    args = ap.parse_args()

    parsed = parse(args.url)
    print(f"platform={parsed.platform} id={parsed.post_id}", file=sys.stderr)
    workdir = pipeline.new_workdir()

    if args.fetch_only:
        result = fetch(parsed, workdir)
        print(json.dumps({
            "kind": result.kind, "author": result.author, "caption": result.caption[:300],
            "videos": [str(p) for p in result.video_paths], "images": [str(p) for p in result.image_paths],
        }, ensure_ascii=False, indent=2))
        return 0

    job = Job(id="smoke")
    pipeline.run(job, parsed, workdir, refresh=True)
    if job.stage == "error":
        print(f"failed during {job.failed_stage}: {job.error}", file=sys.stderr)
        return 1
    print(job.result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
