from datetime import datetime
from pathlib import Path

from nina.core.store.db import open_db
from nina.core.store.kv import ensure_json, get_json, set_json
from nina.skills.presence.models import PresenceState, PresenceStatus

_KEY = "presence"


def load(data_dir: Path) -> PresenceState:
    conn = open_db(data_dir)
    try:
        data = get_json(conn, _KEY)
    finally:
        conn.close()
    if not data:
        return PresenceState(status=PresenceStatus.HOME)
    return PresenceState(
        status=PresenceStatus(data["status"]),
        since=datetime.fromisoformat(data["since"]),
        note=data.get("note", ""),
    )


def save(state: PresenceState, data_dir: Path) -> PresenceStatus | None:
    """Save presence state. Returns old status for transition detection, or None if first save."""
    conn = open_db(data_dir)
    try:
        old_data = get_json(conn, _KEY)
        old_status = PresenceStatus(old_data["status"]) if old_data else None
        set_json(
            conn,
            _KEY,
            {
                "status": state.status.value,
                "since": state.since.isoformat(),
                "note": state.note,
            },
        )
        return old_status
    finally:
        conn.close()


def ensure_default(data_dir: Path) -> None:
    """Create a default presence record on first run (idempotent)."""
    default = PresenceState(status=PresenceStatus.HOME)
    conn = open_db(data_dir)
    try:
        ensure_json(
            conn,
            _KEY,
            {
                "status": default.status.value,
                "since": default.since.isoformat(),
                "note": default.note,
            },
        )
    finally:
        conn.close()
