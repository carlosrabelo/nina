# nina/store/repos/memo.py
"""Memo repository — CRUD over the memos table."""

import sqlite3
import uuid
from datetime import datetime, timezone

from nina.store.models import Memo


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_memo(row: sqlite3.Row) -> Memo:
    return Memo(
        id=row["id"],
        text=row["text"],
        source=row["source"],
        status=row["status"],
        due_date=row["due_date"],
        linked_event_id=row["linked_event_id"],
        obsidian_path=row["obsidian_path"],
        created_at=row["created_at"],
    )


def add(conn: sqlite3.Connection, memo: Memo) -> Memo:
    """Insert a new memo and return it with id and created_at filled."""
    memo.id = str(uuid.uuid4())
    memo.created_at = _now()
    conn.execute(
        """
        INSERT INTO memos (id, text, source, status, due_date,
                           linked_event_id, obsidian_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            memo.id, memo.text, memo.source, memo.status,
            memo.due_date, memo.linked_event_id, memo.obsidian_path,
            memo.created_at,
        ),
    )
    conn.commit()
    return memo


def get(conn: sqlite3.Connection, memo_id: str) -> Memo | None:
    row = conn.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
    return _row_to_memo(row) if row else None


def list_open(conn: sqlite3.Connection) -> list[Memo]:
    rows = conn.execute(
        "SELECT * FROM memos WHERE status = 'open' ORDER BY created_at ASC"
    ).fetchall()
    return [_row_to_memo(r) for r in rows]


def list_all(conn: sqlite3.Connection) -> list[Memo]:
    rows = conn.execute("SELECT * FROM memos ORDER BY created_at DESC").fetchall()
    return [_row_to_memo(r) for r in rows]


def set_status(conn: sqlite3.Connection, memo_id: str, status: str) -> bool:
    """Update status; returns True if a row was affected."""
    cur = conn.execute(
        "UPDATE memos SET status = ? WHERE id = ?", (status, memo_id)
    )
    conn.commit()
    return cur.rowcount > 0


def done(conn: sqlite3.Connection, memo_id: str) -> bool:
    return set_status(conn, memo_id, "done")


def dismiss(conn: sqlite3.Connection, memo_id: str) -> bool:
    return set_status(conn, memo_id, "dismissed")
