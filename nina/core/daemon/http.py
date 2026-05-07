import os
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from nina.core.i18n import t
from nina.core.locale.store import load as load_locale
from nina.skills.presence.models import PresenceState, PresenceStatus
from nina.skills.presence.store import load as load_presence
from nina.skills.presence.store import save as save_presence
from nina.skills.workdays.checker import get_context
from nina.skills.workdays.models import DAY_NAMES_EN
from nina.skills.workdays.store import load as load_schedule
from nina.skills.workdays.store import save as save_schedule

_start_time = time.time()


class CommandRequest(BaseModel):
    command: str  # "/presence work", "/presence dnd note:almoço", etc.


class PresenceUpdate(BaseModel):
    status: PresenceStatus
    note: str = ""


class WorkDayUpdate(BaseModel):
    start: str | None = None  # "HH:MM"
    end: str | None = None  # "HH:MM"
    lunch_start: str | None = None  # "HH:MM"
    lunch_end: str | None = None  # "HH:MM"
    active: bool = True


class NotificationConfigUpdate(BaseModel):
    reminder_minutes: int | None = None
    watch_days: int | None = None


class ScheduleRequest(BaseModel):
    start_time: str  # "HH:MM" (24h)
    title: str
    duration_minutes: int = 60
    calendar_id: str = "primary"


def create_app(tokens_dir: Path, data_dir: Path) -> FastAPI:
    app = FastAPI(title="Nina", docs_url="/docs")

    _api_key = os.getenv("NINA_API_KEY", "")

    def _require_api_key(x_api_key: str = Header(default="")) -> None:
        if _api_key and x_api_key != _api_key:
            raise HTTPException(status_code=403, detail="invalid_api_key")

    def _lang() -> str:
        return load_locale(data_dir).lang

    @app.get("/", dependencies=[Depends(_require_api_key)])
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

    @app.get("/health", dependencies=[Depends(_require_api_key)])
    def health() -> dict:
        uptime = int(time.time() - _start_time)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        return {
            "status": "ok",
            "uptime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "uptime_seconds": uptime,
        }

    @app.get("/presence", dependencies=[Depends(_require_api_key)])
    def get_presence() -> dict:
        state = load_presence(data_dir)
        return {
            "status": state.status.value,
            "since": state.since.isoformat(),
            "note": state.note,
        }

    @app.put("/presence", dependencies=[Depends(_require_api_key)])
    async def set_presence(body: PresenceUpdate) -> dict:
        try:
            state = PresenceState(
                status=body.status,
                since=datetime.now(UTC),
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

    @app.get("/notifications/config", dependencies=[Depends(_require_api_key)])
    def get_notifications_config() -> dict:
        from nina.skills.notifications.store import load as load_notif

        state = load_notif(data_dir)
        return {
            "reminder_minutes": state.config.reminder_minutes,
            "watch_days": state.config.watch_days,
        }

    @app.put("/notifications/config", dependencies=[Depends(_require_api_key)])
    def update_notifications_config(body: NotificationConfigUpdate) -> dict:
        from nina.skills.notifications.store import (
            load as load_notif,
        )
        from nina.skills.notifications.store import (
            save as save_notif,
        )

        state = load_notif(data_dir)
        if body.reminder_minutes is not None:
            if body.reminder_minutes <= 0:
                raise HTTPException(
                    status_code=422, detail="reminder_minutes must be positive"
                )
            state.config.reminder_minutes = body.reminder_minutes
        if body.watch_days is not None:
            if body.watch_days <= 0:
                raise HTTPException(
                    status_code=422, detail="watch_days must be positive"
                )
            state.config.watch_days = body.watch_days
        save_notif(state, data_dir)
        return {
            "reminder_minutes": state.config.reminder_minutes,
            "watch_days": state.config.watch_days,
        }

    # ── calendar schedule ─────────────────────────────────────────────────────

    @app.post("/schedule", dependencies=[Depends(_require_api_key)])
    def create_schedule(body: ScheduleRequest) -> dict:
        from nina.errors import CalendarError
        from nina.skills.calendar.blocking import (
            BlockingIntent,
        )
        from nina.skills.calendar.blocking import (
            execute as execute_blocking,
        )
        from nina.skills.profile.store import load as load_profile

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

    @app.get("/workdays", dependencies=[Depends(_require_api_key)])
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
                    "lunch_start": d.lunch_start.isoformat() if d.lunch_start else None,
                    "lunch_end": d.lunch_end.isoformat() if d.lunch_end else None,
                }
                for d in schedule.days
            ],
        }

    @app.put("/workdays/{day}", dependencies=[Depends(_require_api_key)])
    def update_schedule_day(day: int, body: WorkDayUpdate) -> dict:
        if day < 0 or day > 6:
            raise HTTPException(
                status_code=422, detail="day must be 0 (Monday) to 6 (Sunday)"
            )
        from datetime import time as dt_time

        schedule = load_schedule(data_dir)
        for d in schedule.days:
            if d.day == day:
                d.active = body.active
                d.start = dt_time.fromisoformat(body.start) if body.start else None
                d.end = dt_time.fromisoformat(body.end) if body.end else None
                d.lunch_start = (
                    dt_time.fromisoformat(body.lunch_start)
                    if body.lunch_start
                    else None
                )
                d.lunch_end = (
                    dt_time.fromisoformat(body.lunch_end) if body.lunch_end else None
                )
                break
        save_schedule(schedule, data_dir)
        return {"updated": DAY_NAMES_EN[day]}

    @app.get("/workdays/context", dependencies=[Depends(_require_api_key)])
    def schedule_context() -> dict:
        schedule = load_schedule(data_dir)
        presence = load_presence(data_dir)
        ctx = get_context(schedule, presence, _lang())
        return {
            "label": ctx.label,
            "is_work_time": ctx.is_work_time,
            "is_lunch_time": ctx.is_lunch_time,
            "presence": ctx.presence_status,
            "overtime": ctx.overtime,
            "weekend_work": ctx.weekend_work,
        }

    # ── presence shortcut (MacroDroid) ────────────────────────────────────────

    @app.post("/presence/{status}", dependencies=[Depends(_require_api_key)])
    async def set_presence_path(status: str, note: str = "") -> dict:
        try:
            ps = PresenceStatus(status)
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid_status")
        state = PresenceState(
            status=ps,
            since=datetime.now(UTC),
            note=note,
        )
        save_presence(state, data_dir)
        return {
            "status": state.status.value,
            "since": state.since.isoformat(),
            "note": state.note,
        }

    # ── flat status (MacroDroid polling) ──────────────────────────────────────

    @app.get("/status", dependencies=[Depends(_require_api_key)])
    def get_status() -> dict:
        presence = load_presence(data_dir)
        schedule = load_schedule(data_dir)
        ctx = get_context(schedule, presence, _lang())
        return {
            "presence": presence.status.value,
            "note": presence.note,
            "since": presence.since.isoformat(),
            "label": ctx.label,
            "is_work_time": ctx.is_work_time,
            "is_lunch_time": ctx.is_lunch_time,
            "overtime": ctx.overtime,
            "weekend_work": ctx.weekend_work,
        }

    # ── slash commands (MacroDroid / external) ────────────────────────────────

    @app.post("/command", dependencies=[Depends(_require_api_key)])
    def slash_command(body: CommandRequest) -> dict:
        """Process slash-style commands for external integrations.

        Supported commands:
            /presence {status} [note:...]
            /status
            /health
            /memo {texto}
            /activity {texto}
        """
        cmd = body.command.strip()
        lang = _lang()

        if cmd == "/status":
            presence = load_presence(data_dir)
            msg = f"{presence.status.value} — {presence.note or ''}"
            return {"ok": True, "message": msg}

        if cmd == "/health":
            return {"ok": True, "message": "ok"}

        # /presence {status} [note:...]
        if cmd.startswith("/presence "):
            parts = cmd[len("/presence "):].split(maxsplit=1)
            status_str = parts[0]
            note = ""
            if len(parts) > 1:
                remainder = parts[1]
                if remainder.startswith("note:"):
                    note = remainder[len("note:"):]
                else:
                    note = remainder
            try:
                ps = PresenceStatus(status_str)
            except ValueError:
                valid = ", ".join(s.value for s in PresenceStatus)
                return {"ok": False, "message": f"invalid status. Use: {valid}"}
            state = PresenceState(status=ps, since=datetime.now(UTC), note=note)
            save_presence(state, data_dir)
            label = t(f"presence.label.{ps.value}", lang)
            msg = f"✓ {ps.value} — {label}"
            if note:
                msg += f" ({note})"
            return {"ok": True, "message": msg}

        # /memo {texto}
        if cmd.startswith("/memo "):
            text = cmd[len("/memo "):].strip()
            if not text:
                return {"ok": False, "message": "Usage: /memo {texto}"}
            from nina.core.store.db import open_db
            from nina.core.store.models import Memo
            from nina.core.store.repos import memo as memo_repo
            conn = open_db(data_dir)
            memo_repo.add(conn, Memo(text=text))
            return {"ok": True, "message": f"✓ memo: {text}"}

        # /activity {texto} → log to Google Calendar
        if cmd.startswith("/activity "):
            text = cmd[len("/activity "):].strip()
            if not text:
                return {"ok": False, "message": "Usage: /activity {texto}"}
            from nina.skills.activity_log import models as act_models
            from nina.skills.activity_log.google_writer import log_activity
            from nina.skills.presence.store import load as load_presence_profile
            from nina.skills.profile.store import load as load_profile

            presence = load_presence_profile(data_dir)
            profile = load_profile(data_dir)
            cal_accounts = profile.for_presence(presence.status).calendar
            if not cal_accounts:
                return {"ok": False, "message": "No calendar account."}
            ai = act_models.ActivityIntent(
                action="log", title=text, duration_minutes=60,
            )
            result = log_activity(ai, cal_accounts[0], tokens_dir)
            return {"ok": result.success, "message": result.message}

        return {"ok": False, "message": f"unknown command: {cmd}"}

    return app
