from pathlib import Path

from nina.core.store.db import open_db
from nina.core.store.kv import ensure_json, get_json, set_json
from nina.skills.profile.models import PresenceProfile, Profile

_KEY = "profile"


def load(data_dir: Path) -> Profile:
    conn = open_db(data_dir)
    try:
        data = get_json(conn, _KEY)
    finally:
        conn.close()
    if not data:
        return Profile()
    mapping = {
        presence: PresenceProfile(
            gmail=entry.get("gmail", []),
            calendar=entry.get("calendar", []),
        )
        for presence, entry in data.items()
    }
    return Profile(mapping=mapping)


def save(profile: Profile, data_dir: Path) -> None:
    data = {
        presence: {
            "gmail": p.gmail,
            "calendar": p.calendar,
        }
        for presence, p in profile.mapping.items()
    }
    conn = open_db(data_dir)
    try:
        set_json(conn, _KEY, data)
    finally:
        conn.close()


def ensure_default(data_dir: Path) -> None:
    conn = open_db(data_dir)
    try:
        ensure_json(conn, _KEY, {})
    finally:
        conn.close()
