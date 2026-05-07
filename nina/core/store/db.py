# nina/store/db.py
"""SQLite connection and schema migrations."""

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memos (
    id              TEXT PRIMARY KEY,
    text            TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'text',
    status          TEXT NOT NULL DEFAULT 'open',
    due_date        TEXT,
    linked_event_id TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS actions (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id   TEXT NOT NULL,
    due_date    TEXT,
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS emails (
    message_id      TEXT PRIMARY KEY,
    account         TEXT NOT NULL,
    thread_id       TEXT NOT NULL,
    sender          TEXT NOT NULL,
    subject         TEXT NOT NULL,
    date            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'new',
    follow_up_due   TEXT,
    first_seen_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar_events (
    event_id        TEXT NOT NULL,
    calendar_id     TEXT NOT NULL,
    account         TEXT NOT NULL,
    title           TEXT NOT NULL,
    start_at        TEXT NOT NULL,
    end_at          TEXT NOT NULL,
    briefing_done   INTEGER NOT NULL DEFAULT 0,
    first_seen_at   TEXT NOT NULL,
    PRIMARY KEY (event_id, account)
);
"""


def open_db(data_dir: Path) -> sqlite3.Connection:
    """Open (or create) the Nina database and run migrations."""
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(data_dir / "nina.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()
