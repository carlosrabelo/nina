import json
from pathlib import Path

from nina.profile.models import PresenceProfile, Profile

_FILENAME = "profile.json"


def load(data_dir: Path) -> Profile:
    path = data_dir / _FILENAME
    if not path.exists():
        return Profile()
    data = json.loads(path.read_text())
    mapping = {
        presence: PresenceProfile(
            gmail=entry.get("gmail", []),
            calendar=entry.get("calendar", []),
        )
        for presence, entry in data.items()
    }
    return Profile(mapping=mapping)


def save(profile: Profile, data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    data = {
        presence: {
            "gmail": p.gmail,
            "calendar": p.calendar,
        }
        for presence, p in profile.mapping.items()
    }
    (data_dir / _FILENAME).write_text(json.dumps(data, indent=2))
