import json
from datetime import datetime, timezone
from pathlib import Path

from nina.presence.models import PresenceState, PresenceStatus

_FILENAME = "presence.json"


def load(tokens_dir: Path) -> PresenceState:
    path = tokens_dir / _FILENAME
    if not path.exists():
        return PresenceState(status=PresenceStatus.HOME)
    data = json.loads(path.read_text())
    return PresenceState(
        status=PresenceStatus(data["status"]),
        since=datetime.fromisoformat(data["since"]),
        note=data.get("note", ""),
    )


def save(state: PresenceState, tokens_dir: Path) -> None:
    tokens_dir.mkdir(parents=True, exist_ok=True)
    path = tokens_dir / _FILENAME
    path.write_text(json.dumps({
        "status": state.status.value,
        "since": state.since.isoformat(),
        "note": state.note,
    }, indent=2))
