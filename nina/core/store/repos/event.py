# nina/store/repos/event.py
"""Calendar event repository — placeholder for future Calendar sync."""

from datetime import UTC, datetime

import psycopg

from nina.core.store.models import EventRecord


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_record(row: dict) -> EventRecord:
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


def upsert(conn: psycopg.Connection[dict], record: EventRecord) -> None:
    if not record.first_seen_at:
        record.first_seen_at = _now()
    conn.execute(
        """
        INSERT INTO calendar_events
            (event_id, calendar_id, account, title, start_at, end_at,
             briefing_done, first_seen_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(event_id, account) DO UPDATE SET
            title         = EXCLUDED.title,
            start_at      = EXCLUDED.start_at,
            end_at        = EXCLUDED.end_at,
            briefing_done = EXCLUDED.briefing_done
        """,
        (
            record.event_id, record.calendar_id, record.account,
            record.title, record.start_at, record.end_at,
            record.briefing_done, record.first_seen_at,
        ),
    )
    conn.commit()


def get(
    conn: psycopg.Connection[dict], event_id: str, account: str
) -> EventRecord | None:
    row = conn.execute(
        "SELECT * FROM calendar_events WHERE event_id = %s AND account = %s",
        (event_id, account),
    ).fetchone()
    return _row_to_record(row) if row else None


def list_pending_briefing(conn: psycopg.Connection[dict]) -> list[EventRecord]:
    rows = conn.execute(
        "SELECT * FROM calendar_events WHERE briefing_done = FALSE ORDER BY start_at ASC"
    ).fetchall()
    return [_row_to_record(r) for r in rows]
