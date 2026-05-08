"""`nina migrate` — one-off migration helpers."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from nina.core.store.db import open_db
from nina.core.store.kv import set_json


def _data_dir() -> Path:
    import os

    return Path(os.environ.get("DATA_DIR", "data"))


def _migrate_sqlite_table(
    src: sqlite3.Connection,
    dst,
    *,
    table: str,
    columns: list[str],
    conflict: str,
    update_cols: list[str] | None = None,
) -> int:
    rows = src.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
    if not rows:
        return 0

    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)

    if update_cols:
        set_parts = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
        sql = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT {conflict} DO UPDATE SET {set_parts}"
        )
    else:
        sql = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT {conflict} DO NOTHING"
        )

    for r in rows:
        dst.execute(sql, tuple(r))
    dst.commit()
    return len(rows)


def _migrate_json_file_to_kv(dst, data_dir: Path, filename: str, key: str) -> bool:
    path = data_dir / filename
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
    except Exception:
        return False
    set_json(dst, key, data if isinstance(data, dict) else {"value": data})
    return True


def cmd_to_postgres(args: argparse.Namespace) -> None:
    data_dir = _data_dir()

    dst = open_db(data_dir)
    try:
        # 1) migrate SQLite → Postgres
        sqlite_path = data_dir / "nina.db"
        if sqlite_path.exists():
            src = sqlite3.connect(sqlite_path)
            try:
                memos = _migrate_sqlite_table(
                    src,
                    dst,
                    table="memos",
                    columns=[
                        "id",
                        "text",
                        "source",
                        "status",
                        "due_date",
                        "linked_event_id",
                        "created_at",
                    ],
                    conflict="(id)",
                    update_cols=[
                        "text",
                        "source",
                        "status",
                        "due_date",
                        "linked_event_id",
                        "created_at",
                    ],
                )
                actions = _migrate_sqlite_table(
                    src,
                    dst,
                    table="actions",
                    columns=[
                        "id",
                        "type",
                        "source_type",
                        "source_id",
                        "due_date",
                        "status",
                        "created_at",
                    ],
                    conflict="(id)",
                    update_cols=[
                        "type",
                        "source_type",
                        "source_id",
                        "due_date",
                        "status",
                        "created_at",
                    ],
                )
                emails = _migrate_sqlite_table(
                    src,
                    dst,
                    table="emails",
                    columns=[
                        "message_id",
                        "account",
                        "thread_id",
                        "sender",
                        "subject",
                        "date",
                        "status",
                        "follow_up_due",
                        "first_seen_at",
                    ],
                    conflict="(message_id)",
                    update_cols=["status", "follow_up_due"],
                )
                events = _migrate_sqlite_table(
                    src,
                    dst,
                    table="calendar_events",
                    columns=[
                        "event_id",
                        "calendar_id",
                        "account",
                        "title",
                        "start_at",
                        "end_at",
                        "briefing_done",
                        "first_seen_at",
                    ],
                    conflict="(event_id, account)",
                    update_cols=["title", "start_at", "end_at", "briefing_done"],
                )
            finally:
                src.close()
        else:
            memos = actions = emails = events = 0

        # 2) migrate JSON files → kv_state
        migrated = []
        for filename, key in [
            ("presence.json", "presence"),
            ("workdays.json", "workdays"),
            ("notifications.json", "notifications"),
            ("profile.json", "profile"),
            ("locale.json", "locale"),
        ]:
            if _migrate_json_file_to_kv(dst, data_dir, filename, key):
                migrated.append(filename)

    finally:
        dst.close()

    print("Migration complete.")
    print(f"  memos:          {memos}")
    print(f"  actions:        {actions}")
    print(f"  emails:         {emails}")
    print(f"  calendar_events:{events}")
    if migrated:
        print(f"  kv_state:       {', '.join(migrated)}")
    else:
        print("  kv_state:       (no JSON files found)")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("migrate", help="Data migrations")
    g = p.add_subparsers(dest="action", required=True)

    g.add_parser(
        "to-postgres",
        help="Migrate legacy SQLite + JSON files in DATA_DIR to PostgreSQL",
    ).set_defaults(func=cmd_to_postgres)

