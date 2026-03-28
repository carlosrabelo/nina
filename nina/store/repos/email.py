# nina/store/repos/email.py
"""Email repository — placeholder for future Gmail sync."""

import sqlite3
from datetime import datetime, timezone

from nina.store.models import EmailRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_record(row: sqlite3.Row) -> EmailRecord:
    return EmailRecord(
        message_id=row["message_id"],
        account=row["account"],
        thread_id=row["thread_id"],
        sender=row["sender"],
        subject=row["subject"],
        date=row["date"],
        status=row["status"],
        follow_up_due=row["follow_up_due"],
        first_seen_at=row["first_seen_at"],
    )


def upsert(conn: sqlite3.Connection, record: EmailRecord) -> None:
    if not record.first_seen_at:
        record.first_seen_at = _now()
    conn.execute(
        """
        INSERT INTO emails (message_id, account, thread_id, sender, subject,
                            date, status, follow_up_due, first_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
            status       = excluded.status,
            follow_up_due = excluded.follow_up_due
        """,
        (
            record.message_id, record.account, record.thread_id,
            record.sender, record.subject, record.date,
            record.status, record.follow_up_due, record.first_seen_at,
        ),
    )
    conn.commit()


def get(conn: sqlite3.Connection, message_id: str) -> EmailRecord | None:
    row = conn.execute(
        "SELECT * FROM emails WHERE message_id = ?", (message_id,)
    ).fetchone()
    return _row_to_record(row) if row else None


def list_by_status(conn: sqlite3.Connection, status: str) -> list[EmailRecord]:
    rows = conn.execute(
        "SELECT * FROM emails WHERE status = ? ORDER BY date DESC", (status,)
    ).fetchall()
    return [_row_to_record(r) for r in rows]
