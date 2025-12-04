"""Simple SQLite helpers for persisting event metadata."""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
from contextlib import contextmanager

_DDL = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    clip_path TEXT,
    snapshot_path TEXT,
    face_detected INTEGER DEFAULT 0,
    duration INTEGER
)
"""


def init_db(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(_DDL)


@contextmanager
def db_connection(path: str):
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()


def record_event(
    path: str,
    *,
    camera_id: str,
    event_type: str,
    clip_path: str | None,
    snapshot_path: str | None,
    face_detected: bool,
    duration: int,
    timestamp: dt.datetime | None = None,
) -> None:
    init_db(path)
    when = (timestamp or dt.datetime.utcnow()).isoformat()
    with db_connection(path) as conn:
        conn.execute(
            """
            INSERT INTO events (timestamp, camera_id, event_type, clip_path, snapshot_path, face_detected, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                when,
                camera_id,
                event_type,
                clip_path,
                snapshot_path,
                1 if face_detected else 0,
                duration,
            ),
        )
        conn.commit()
