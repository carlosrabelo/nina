# nina/store/repos/event.py
"""Calendar event repository — placeholder for future Calendar sync."""

import sqlite3
from datetime import datetime, timezone

from nina.store.models import EventRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_record(row: sqlite3.Row) -> EventRecord:
    return EventRecord(
        event_id=row["event_id"],
        calendar_id=row["calendar_id"],
        account=row["account"],
        title=row["title"],
        start_at=row["start_at"],
        end_at=row["end_at"],
        briefing_done=bool(row["briefing_done"]),
        first_seen_at=row["first_seen_at"],
    )


def upsert(conn: sqlite3.Connection, record: EventRecord) -> None:
    if not record.first_seen_at:
        record.first_seen_at = _now()
    conn.execute(
        """
        INSERT INTO calendar_events
            (event_id, calendar_id, account, title, start_at, end_at,
             briefing_done, first_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_id, account) DO UPDATE SET
            title         = excluded.title,
            start_at      = excluded.start_at,
            end_at        = excluded.end_at,
            briefing_done = excluded.briefing_done
        """,
        (
            record.event_id, record.calendar_id, record.account,
            record.title, record.start_at, record.end_at,
            int(record.briefing_done), record.first_seen_at,
        ),
    )
    conn.commit()


def get(conn: sqlite3.Connection, event_id: str, account: str) -> EventRecord | None:
    row = conn.execute(
        "SELECT * FROM calendar_events WHERE event_id = ? AND account = ?",
        (event_id, account),
    ).fetchone()
    return _row_to_record(row) if row else None


def list_pending_briefing(conn: sqlite3.Connection) -> list[EventRecord]:
    rows = conn.execute(
        "SELECT * FROM calendar_events WHERE briefing_done = 0 ORDER BY start_at ASC"
    ).fetchall()
    return [_row_to_record(r) for r in rows]
