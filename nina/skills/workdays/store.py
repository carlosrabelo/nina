from datetime import time
from pathlib import Path

from nina.core.store.db import open_db
from nina.core.store.kv import ensure_json, get_json, set_json
from nina.skills.workdays.models import WorkDay, WorkSchedule, default_schedule

_KEY = "workdays"


def load(data_dir: Path) -> WorkSchedule:
    conn = open_db(data_dir)
    try:
        data = get_json(conn, _KEY)
    finally:
        conn.close()
    if not data:
        return default_schedule()
    days = []
    for d in data["days"]:
        days.append(WorkDay(
            day=d["day"],
            start=time.fromisoformat(d["start"]) if d.get("start") else None,
            end=time.fromisoformat(d["end"]) if d.get("end") else None,
            lunch_start=time.fromisoformat(d["lunch_start"]) if d.get("lunch_start") else None,
            lunch_end=time.fromisoformat(d["lunch_end"]) if d.get("lunch_end") else None,
            active=d.get("active", False),
        ))
    return WorkSchedule(days=days, timezone=data.get("timezone", "America/Sao_Paulo"))


def save(schedule: WorkSchedule, data_dir: Path) -> None:
    data = {
        "timezone": schedule.timezone,
        "days": [
            {
                "day": d.day,
                "start": d.start.isoformat() if d.start else None,
                "end": d.end.isoformat() if d.end else None,
                "lunch_start": d.lunch_start.isoformat() if d.lunch_start else None,
                "lunch_end": d.lunch_end.isoformat() if d.lunch_end else None,
                "active": d.active,
            }
            for d in schedule.days
        ],
    }
    conn = open_db(data_dir)
    try:
        set_json(conn, _KEY, data)
    finally:
        conn.close()


def ensure_default(data_dir: Path) -> None:
    schedule = default_schedule()
    data = {
        "timezone": schedule.timezone,
        "days": [
            {
                "day": d.day,
                "start": d.start.isoformat() if d.start else None,
                "end": d.end.isoformat() if d.end else None,
                "lunch_start": d.lunch_start.isoformat() if d.lunch_start else None,
                "lunch_end": d.lunch_end.isoformat() if d.lunch_end else None,
                "active": d.active,
            }
            for d in schedule.days
        ],
    }
    conn = open_db(data_dir)
    try:
        ensure_json(conn, _KEY, data)
    finally:
        conn.close()
