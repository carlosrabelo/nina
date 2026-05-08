# nina/store/repos/memo.py
"""Memo repository — CRUD over the memos table."""

import uuid
from datetime import UTC, datetime

import psycopg

from nina.core.store.models import Memo


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_memo(row: dict) -> Memo:
    return Memo(
        id=row["id"],
        text=row["text"],
        source=row["source"],
        status=row["status"],
        due_date=row["due_date"],
        linked_event_id=row["linked_event_id"],
        created_at=row["created_at"],
    )


def add(conn: psycopg.Connection[dict], memo: Memo) -> Memo:
    """Insert a new memo and return it with id and created_at filled."""
    memo.id = str(uuid.uuid4())
    memo.created_at = _now()
    conn.execute(
        """
        INSERT INTO memos (id, text, source, status, due_date,
                           linked_event_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            memo.id, memo.text, memo.source, memo.status,
            memo.due_date, memo.linked_event_id, memo.created_at,
        ),
    )
    conn.commit()
    return memo


def get(conn: psycopg.Connection[dict], memo_id: str) -> Memo | None:
    row = conn.execute("SELECT * FROM memos WHERE id = %s", (memo_id,)).fetchone()
    return _row_to_memo(row) if row else None


def list_open(conn: psycopg.Connection[dict]) -> list[Memo]:
    rows = conn.execute(
        "SELECT * FROM memos WHERE status = 'open' ORDER BY created_at ASC"
    ).fetchall()
    return [_row_to_memo(r) for r in rows]


def list_all(conn: psycopg.Connection[dict]) -> list[Memo]:
    rows = conn.execute("SELECT * FROM memos ORDER BY created_at DESC").fetchall()
    return [_row_to_memo(r) for r in rows]


def set_status(conn: psycopg.Connection[dict], memo_id: str, status: str) -> bool:
    """Update status; returns True if a row was affected."""
    cur = conn.execute(
        "UPDATE memos SET status = %s WHERE id = %s", (status, memo_id)
    )
    conn.commit()
    return cur.rowcount > 0


def done(conn: psycopg.Connection[dict], memo_id: str) -> bool:
    return set_status(conn, memo_id, "done")


def dismiss(conn: psycopg.Connection[dict], memo_id: str) -> bool:
    return set_status(conn, memo_id, "dismissed")
