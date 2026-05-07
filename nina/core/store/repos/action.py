# nina/store/repos/action.py
"""Action repository — placeholder for follow-up and reminder tracking."""

import sqlite3
import uuid
from datetime import UTC, datetime

from nina.core.store.models import Action


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_action(row: sqlite3.Row) -> Action:
    return Action(
        id=row["id"],
        type=row["type"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        due_date=row["due_date"],
        status=row["status"],
        created_at=row["created_at"],
    )


def add(conn: sqlite3.Connection, action: Action) -> Action:
    action.id = str(uuid.uuid4())
    action.created_at = _now()
    conn.execute(
        """
        INSERT INTO actions (id, type, source_type, source_id, due_date,
                             status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            action.id, action.type, action.source_type, action.source_id,
            action.due_date, action.status, action.created_at,
        ),
    )
    conn.commit()
    return action


def list_open(conn: sqlite3.Connection) -> list[Action]:
    rows = conn.execute(
        "SELECT * FROM actions WHERE status = 'open' ORDER BY due_date ASC NULLS LAST"
    ).fetchall()
    return [_row_to_action(r) for r in rows]


def close(conn: sqlite3.Connection, action_id: str) -> bool:
    cur = conn.execute(
        "UPDATE actions SET status = 'closed' WHERE id = ?", (action_id,)
    )
    conn.commit()
    return cur.rowcount > 0
