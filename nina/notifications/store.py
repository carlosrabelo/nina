"""Persist notification state to tokens/notifications.json."""

from __future__ import annotations

import json
from pathlib import Path

from nina.notifications.models import (
    KnownEvent,
    NotificationConfig,
    NotificationState,
    QueuedNotification,
)

_FILENAME = "notifications.json"


def load(tokens_dir: Path) -> NotificationState:
    path = tokens_dir / _FILENAME
    if not path.exists():
        return NotificationState()
    try:
        data = json.loads(path.read_text())
    except Exception:
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


def save(state: NotificationState, tokens_dir: Path) -> None:
    tokens_dir.mkdir(parents=True, exist_ok=True)
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
    (tokens_dir / _FILENAME).write_text(json.dumps(data, indent=2, ensure_ascii=False))
