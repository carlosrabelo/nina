import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from nina.i18n import t
from nina.locale.store import load as load_locale
from nina.presence.models import PresenceState, PresenceStatus
from nina.presence.store import load as load_presence
from nina.presence.store import save as save_presence
from nina.workdays.checker import get_context
from nina.workdays.models import DAY_NAMES_EN
from nina.workdays.store import load as load_schedule
from nina.workdays.store import save as save_schedule

_start_time = time.time()


class PresenceUpdate(BaseModel):
    status: PresenceStatus
    note: str = ""


class WorkDayUpdate(BaseModel):
    start: str | None = None   # "HH:MM"
    end: str | None = None     # "HH:MM"
    active: bool = True


def create_app(tokens_dir: Path) -> FastAPI:
    app = FastAPI(title="Nina", docs_url="/docs")

    def _lang() -> str:
        return load_locale(tokens_dir).lang

    @app.get("/")
    def root() -> dict:
        uptime = int(time.time() - _start_time)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        presence = load_presence(tokens_dir)
        schedule = load_schedule(tokens_dir)
        ctx = get_context(schedule, presence, _lang())
        return {
            "nina": "ok",
            "uptime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "context": ctx.label,
            "presence": {
                "status": presence.status.value,
                "since": presence.since.isoformat(),
                "note": presence.note,
            },
            "work_time": ctx.is_work_time,
            "docs": "/docs",
        }

    @app.get("/health")
    def health() -> dict:
        uptime = int(time.time() - _start_time)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        return {
            "status": "ok",
            "uptime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "uptime_seconds": uptime,
        }

    @app.get("/presence")
    def get_presence() -> dict:
        state = load_presence(tokens_dir)
        return {
            "status": state.status.value,
            "since": state.since.isoformat(),
            "note": state.note,
        }

    @app.put("/presence")
    def set_presence(body: PresenceUpdate) -> dict:
        try:
            state = PresenceState(
                status=body.status,
                since=datetime.now(timezone.utc),
                note=body.note,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        save_presence(state, tokens_dir)
        return {
            "status": state.status.value,
            "since": state.since.isoformat(),
            "note": state.note,
        }

    # ── schedule ──────────────────────────────────────────────────────────────

    @app.get("/workdays")
    def get_schedule() -> dict:
        lang = _lang()
        schedule = load_schedule(tokens_dir)
        return {
            "timezone": schedule.timezone,
            "days": [
                {
                    "day": d.day,
                    "name": t(f"day.{d.day}", lang),
                    "active": d.active,
                    "start": d.start.isoformat() if d.start else None,
                    "end": d.end.isoformat() if d.end else None,
                }
                for d in schedule.days
            ],
        }

    @app.put("/workdays/{day}")
    def update_schedule_day(day: int, body: WorkDayUpdate) -> dict:
        if day < 0 or day > 6:
            raise HTTPException(status_code=422, detail="day must be 0 (Monday) to 6 (Sunday)")
        from datetime import time as dt_time
        schedule = load_schedule(tokens_dir)
        for d in schedule.days:
            if d.day == day:
                d.active = body.active
                d.start = dt_time.fromisoformat(body.start) if body.start else None
                d.end = dt_time.fromisoformat(body.end) if body.end else None
                break
        save_schedule(schedule, tokens_dir)
        return {"updated": DAY_NAMES_EN[day]}

    @app.get("/workdays/context")
    def schedule_context() -> dict:
        schedule = load_schedule(tokens_dir)
        presence = load_presence(tokens_dir)
        ctx = get_context(schedule, presence, _lang())
        return {
            "label": ctx.label,
            "is_work_time": ctx.is_work_time,
            "presence": ctx.presence_status,
            "overtime": ctx.overtime,
            "weekend_work": ctx.weekend_work,
        }

    return app
