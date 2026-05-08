"""Persist notification state to data/notifications.json."""

from __future__ import annotations

from pathlib import Path

from nina.core.store.db import open_db
from nina.core.store.kv import ensure_json, get_json, set_json
from nina.skills.notifications.models import (
    KnownEvent,
    NotificationConfig,
    NotificationState,
    QueuedNotification,
)

_KEY = "notifications"


def load(data_dir: Path) -> NotificationState:
    conn = open_db(data_dir)
    try:
        data = get_json(conn, _KEY)
    finally:
        conn.close()
    if not data:
        return NotificationState()

    cfg = data.get("config", {})
    config = NotificationConfig(
        reminder_minutes=int(cfg.get("reminder_minutes", 15)),
        watch_days=int(cfg.get("watch_days", 7)),
    )

    known_events: dict[str, KnownEvent] = {}
    for key, ev in data.get("known_events", {}).items():
        known_events[key] = KnownEvent(
            event_id=ev["event_id"],
            account=ev["account"],
            title=ev["title"],
            start=ev["start"],
            end=ev["end"],
            updated=ev["updated"],
        )

    queue = [
        QueuedNotification(id=q["id"], message=q["message"])
        for q in data.get("queue", [])
    ]

    return NotificationState(
        config=config,
        reminders_sent=data.get("reminders_sent", {}),
        known_events=known_events,
        queue=queue,
        last_can_notify=data.get("last_can_notify", True),
    )


def save(state: NotificationState, data_dir: Path) -> None:
    data = {
        "config": {
            "reminder_minutes": state.config.reminder_minutes,
            "watch_days": state.config.watch_days,
        },
        "reminders_sent": state.reminders_sent,
        "known_events": {
            key: {
                "event_id": ev.event_id,
                "account": ev.account,
                "title": ev.title,
                "start": ev.start,
                "end": ev.end,
                "updated": ev.updated,
            }
            for key, ev in state.known_events.items()
        },
        "queue": [{"id": q.id, "message": q.message} for q in state.queue],
        "last_can_notify": state.last_can_notify,
    }
    conn = open_db(data_dir)
    try:
        set_json(conn, _KEY, data)
    finally:
        conn.close()


def ensure_default(data_dir: Path) -> None:
    conn = open_db(data_dir)
    try:
        ensure_json(
            conn,
            _KEY,
            {
                "config": {"reminder_minutes": 15, "watch_days": 7},
                "reminders_sent": {},
                "known_events": {},
                "queue": [],
                "last_can_notify": True,
            },
        )
    finally:
        conn.close()
