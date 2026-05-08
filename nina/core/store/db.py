"""PostgreSQL connection and schema migrations."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

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
    briefing_done   BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_at   TEXT NOT NULL,
    PRIMARY KEY (event_id, account)
);

CREATE TABLE IF NOT EXISTS kv_state (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def open_db(data_dir: Path) -> psycopg.Connection[dict]:
    """Open a PostgreSQL connection and run schema migrations.

    `data_dir` is kept for backwards-compatible call sites, but PostgreSQL
    connection is configured exclusively via DATABASE_URL.
    """
    _ = data_dir
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required (PostgreSQL is the primary Nina store)"
        )

    conn: psycopg.Connection[dict] = psycopg.connect(url, row_factory=dict_row)
    _migrate(conn)
    return conn


def _migrate(conn: psycopg.Connection[dict]) -> None:
    conn.execute(_SCHEMA)
    conn.commit()
