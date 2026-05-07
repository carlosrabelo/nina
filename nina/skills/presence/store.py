import json
from datetime import datetime
from pathlib import Path

from nina.skills.presence.models import PresenceState, PresenceStatus

_FILENAME = "presence.json"


def load(data_dir: Path) -> PresenceState:
    path = data_dir / _FILENAME
    if not path.exists():
        return PresenceState(status=PresenceStatus.HOME)
    data = json.loads(path.read_text())
    return PresenceState(
        status=PresenceStatus(data["status"]),
        since=datetime.fromisoformat(data["since"]),
        note=data.get("note", ""),
    )


def save(state: PresenceState, data_dir: Path) -> PresenceStatus | None:
    """Save presence state. Returns old status for transition detection, or None if first save."""
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / _FILENAME

    old_status = None
    if path.exists():
        old_data = json.loads(path.read_text())
        old_status = PresenceStatus(old_data["status"])

    path.write_text(json.dumps({
        "status": state.status.value,
        "since": state.since.isoformat(),
        "note": state.note,
    }, indent=2))

    return old_status
