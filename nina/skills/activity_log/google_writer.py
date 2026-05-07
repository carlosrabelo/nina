"""Write activity log entries to Google Calendar as past events."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from nina.errors import CalendarError
from nina.skills.activity_log.models import ActivityIntent, ActivityResult

# Time-of-day hints → default hour
_TIME_HINTS: dict[str, int] = {
    "manha": 9, "manhã": 9, "morning": 9, "cedo": 8,
    "meio-dia": 12, "meio dia": 12, "almoco": 12, "almoço": 12,
    "lunch": 12, "tarde": 14, "afternoon": 14,
    "noite": 19, "evening": 19, "night": 20,
}


def _round_down_15(dt: datetime) -> datetime:
    """Round DOWN to the nearest 15-minute block."""
    remainder = dt.minute % 15
    return (dt - timedelta(minutes=remainder)).replace(second=0, microsecond=0)


def _round_up_15(dt: datetime) -> datetime:
    """Round UP to the next 15-minute block."""
    remainder = dt.minute % 15
    if remainder != 0:
        dt = dt + timedelta(minutes=15 - remainder)
    return dt.replace(second=0, microsecond=0)


def _infer_hour_from_text(text: str) -> int | None:
    """Extract a time-of-day hint from text."""
    lower = text.lower()
    for hint, hour in _TIME_HINTS.items():
        if hint in lower:
            return hour
    return None


def _default_midpoint(tz_name: str) -> datetime:
    """Return a sensible default: 11:00 (midpoint of typical workday)."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    return now.replace(hour=11, minute=0, second=0, microsecond=0)


def log_activity(
    intent: ActivityIntent,
    account: str,
    tokens_dir: Path,
    tz_name: str = "America/Cuiaba",
    calendar_id: str = "primary",
) -> ActivityResult:
    """Create a past event in Google Calendar for an activity log entry.

    Rounds start/end to 15-minute blocks. Infers hour from text hints
    or defaults to workday midpoint (11:00).
    """
    from zoneinfo import ZoneInfo

    from nina.integrations.google.calendar.client import CalendarClient

    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    duration = intent.duration_minutes or 60

    # ── Resolve start time ─────────────────────────────────────────────
    if intent.start and intent.end:
        # Explicit times provided — round them
        start = _round_down_15(intent.start.replace(tzinfo=tz))
        end = _round_up_15(intent.end.replace(tzinfo=tz))
    elif intent.start:
        # Only start provided — compute end from duration
        start = _round_down_15(intent.start.replace(tzinfo=tz))
        end = _round_up_15(start + timedelta(minutes=duration))
    else:
        # No time given — infer from text or default to 11:00
        base_date = intent.target_date or now.date()
        hour = _infer_hour_from_text(intent.title or "")
        if hour is None:
            # Default: midpoint of workday
            base = _default_midpoint(tz_name)
            start = _round_down_15(base.replace(
                year=base_date.year, month=base_date.month,
                day=base_date.day,
            ))
        else:
            start = _round_down_15(datetime(
                base_date.year, base_date.month, base_date.day,
                hour, 0, tzinfo=tz,
            ))
        end = _round_up_15(start + timedelta(minutes=duration))

    title = intent.title or "Atividade registrada"
    description = f"Registrado por Nina — Activity Log\nEntrada: {intent.title}"

    try:
        client = CalendarClient(account, tokens_dir)
        event = client.create_event(
            title=title,
            start=start,
            end=end,
            calendar_id=calendar_id,
            description=description,
        )
    except CalendarError as e:
        return ActivityResult(success=False, message=f"Erro ao criar evento: {e}")

    return ActivityResult(
        success=True,
        title=event.title,
        start=start,
        end=end,
        link=event.link,
        account=account,
        message=f"✓ {title}\n{start.strftime('%d/%m %H:%M')} → {end.strftime('%H:%M')}",
    )
