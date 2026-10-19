"""SQLite cache of finished results, so re-pasting a post is free."""

import sqlite3
import threading
import time

from app.config import settings
from app.models import Result

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.data_dir / "storypulls.db")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS results (key TEXT PRIMARY KEY, created_at REAL, payload TEXT)"
    )
    return conn


def get(key: str) -> Result | None:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT payload FROM results WHERE key = ?", (key,)).fetchone()
    return Result.model_validate_json(row[0]) if row else None


def put(key: str, result: Result) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO results (key, created_at, payload) VALUES (?, ?, ?)",
            (key, time.time(), result.model_dump_json()),
        )
