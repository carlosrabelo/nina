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


class NotificationConfigUpdate(BaseModel):
    reminder_minutes: int | None = None
    watch_days: int | None = None


class ScheduleRequest(BaseModel):
    start_time: str           # "HH:MM" (24h)
    title: str
    duration_minutes: int = 60
    calendar_id: str = "primary"


def create_app(tokens_dir: Path, data_dir: Path) -> FastAPI:
    app = FastAPI(title="Nina", docs_url="/docs")

    def _lang() -> str:
        return load_locale(data_dir).lang

    @app.get("/")
    def root() -> dict:
        uptime = int(time.time() - _start_time)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        presence = load_presence(data_dir)
        schedule = load_schedule(data_dir)
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
        state = load_presence(data_dir)
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
        save_presence(state, data_dir)
        return {
            "status": state.status.value,
            "since": state.since.isoformat(),
            "note": state.note,
        }

    # ── notifications ─────────────────────────────────────────────────────────

    @app.get("/notifications/config")
    def get_notifications_config() -> dict:
        from nina.notifications.store import load as load_notif
        state = load_notif(data_dir)
        return {
            "reminder_minutes": state.config.reminder_minutes,
            "watch_days": state.config.watch_days,
        }

    @app.put("/notifications/config")
    def update_notifications_config(body: NotificationConfigUpdate) -> dict:
        from nina.notifications.store import load as load_notif, save as save_notif
        state = load_notif(data_dir)
        if body.reminder_minutes is not None:
            if body.reminder_minutes <= 0:
                raise HTTPException(status_code=422, detail="reminder_minutes must be positive")
            state.config.reminder_minutes = body.reminder_minutes
        if body.watch_days is not None:
            if body.watch_days <= 0:
                raise HTTPException(status_code=422, detail="watch_days must be positive")
            state.config.watch_days = body.watch_days
        save_notif(state, data_dir)
        return {
            "reminder_minutes": state.config.reminder_minutes,
            "watch_days": state.config.watch_days,
        }

    # ── calendar schedule ─────────────────────────────────────────────────────

    @app.post("/schedule")
    def create_schedule(body: ScheduleRequest) -> dict:
        from nina.errors import CalendarError
        from nina.google.calendar.blocking import BlockingIntent, execute as execute_blocking
        from nina.profile.store import load as load_profile
        schedule = load_schedule(data_dir)
        presence = load_presence(data_dir)
        profile = load_profile(data_dir)
        cal_accounts = profile.for_presence(presence.status).calendar
        if not cal_accounts:
            raise HTTPException(status_code=409, detail="no_calendar_account")
        intent = BlockingIntent(
            action="block_calendar",
            title=body.title,
            duration_minutes=body.duration_minutes,
            start_time=body.start_time,
        )
        try:
            result = execute_blocking(
                intent,
                account=cal_accounts[0],
                tokens_dir=tokens_dir,
                tz_name=schedule.timezone,
                calendar_id=body.calendar_id,
            )
        except CalendarError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        return {
            "event_title": result.event_title,
            "start": result.start.isoformat(),
            "end": result.end.isoformat(),
            "conflicts": result.conflicts,
            "link": result.link,
            "account": cal_accounts[0],
        }

    # ── workdays ──────────────────────────────────────────────────────────────

    @app.get("/workdays")
    def get_schedule() -> dict:
        lang = _lang()
        schedule = load_schedule(data_dir)
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
        schedule = load_schedule(data_dir)
        for d in schedule.days:
            if d.day == day:
                d.active = body.active
                d.start = dt_time.fromisoformat(body.start) if body.start else None
                d.end = dt_time.fromisoformat(body.end) if body.end else None
                break
        save_schedule(schedule, data_dir)
        return {"updated": DAY_NAMES_EN[day]}

    @app.get("/workdays/context")
    def schedule_context() -> dict:
        schedule = load_schedule(data_dir)
        presence = load_presence(data_dir)
        ctx = get_context(schedule, presence, _lang())
        return {
            "label": ctx.label,
            "is_work_time": ctx.is_work_time,
            "presence": ctx.presence_status,
            "overtime": ctx.overtime,
            "weekend_work": ctx.weekend_work,
        }

    return app
