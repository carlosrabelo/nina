import json
from datetime import time
from pathlib import Path

from nina.workdays.models import WorkDay, WorkSchedule, default_schedule

_FILENAME = "workdays.json"


def load(data_dir: Path) -> WorkSchedule:
    path = data_dir / _FILENAME
    if not path.exists():
        return default_schedule()
    data = json.loads(path.read_text())
    days = []
    for d in data["days"]:
        days.append(WorkDay(
            day=d["day"],
            start=time.fromisoformat(d["start"]) if d.get("start") else None,
            end=time.fromisoformat(d["end"]) if d.get("end") else None,
            active=d.get("active", False),
        ))
    return WorkSchedule(days=days, timezone=data.get("timezone", "America/Sao_Paulo"))


def save(schedule: WorkSchedule, data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / _FILENAME
    path.write_text(json.dumps({
        "timezone": schedule.timezone,
        "days": [
            {
                "day": d.day,
                "start": d.start.isoformat() if d.start else None,
                "end": d.end.isoformat() if d.end else None,
                "active": d.active,
            }
            for d in schedule.days
        ],
    }, indent=2))
