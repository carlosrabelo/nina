from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb


def get_json(conn: psycopg.Connection[dict], key: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT value FROM kv_state WHERE key = %s", (key,)).fetchone()
    if not row:
        return None
    value = row["value"]
    if isinstance(value, dict):
        return value
    # psycopg should decode jsonb → dict automatically, but be defensive.
    return dict(value)


def set_json(conn: psycopg.Connection[dict], key: str, value: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO kv_state (key, value)
        VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE
        SET value = EXCLUDED.value,
            updated_at = now()
        """,
        (key, Jsonb(value)),
    )
    conn.commit()


def ensure_json(
    conn: psycopg.Connection[dict], key: str, value: dict[str, Any]
) -> bool:
    """Insert default value if key missing. Returns True if inserted."""
    cur = conn.execute(
        """
        INSERT INTO kv_state (key, value)
        VALUES (%s, %s)
        ON CONFLICT (key) DO NOTHING
        """,
        (key, Jsonb(value)),
    )
    conn.commit()
    return cur.rowcount > 0

