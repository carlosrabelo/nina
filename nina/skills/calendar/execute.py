"""Unified calendar read execution (Telegram, console, router).

Uses `Profile.best_calendar_accounts` so context words like "trabalho"
pick the right Google account.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from nina.core.i18n import t
from nina.errors import CalendarError
from nina.integrations.google.calendar.client import CalendarClient, Event
from nina.skills.presence.store import load as load_presence
from nina.skills.profile.store import load as load_profile
from nina.skills.workdays.store import load as load_workdays

Window = Literal["upcoming", "today", "tomorrow", "week", "days", "on_date"]
Period = Literal["full", "morning", "afternoon"]

_MIN_GAP_MINUTES = 30


@dataclass(frozen=True)
class CalendarReadRequest:
    """What to read from Google Calendar (no writes — blocking stays separate)."""

    action: Literal["list", "search", "free_busy"] = "list"
    window: Window = "upcoming"
    span_days: int | None = None
    keyword: str = ""
    period: Period = "full"
    on_date: date | None = None  # when window == "on_date"


def request_from_entities(action: str, entities: dict[str, Any]) -> CalendarReadRequest:
    """Build a request from LocalIntent.entities or equivalent dict."""
    act = action if action in ("list", "search", "free_busy") else "list"
    raw_w = str(entities.get("calendar_window") or "upcoming").lower()
    if raw_w not in ("upcoming", "today", "tomorrow", "week", "days", "on_date"):
        raw_w = "upcoming"
    window: Window = raw_w  # type: ignore[assignment]

    span = entities.get("calendar_span_days")
    if isinstance(span, str) and span.isdigit():
        span = int(span)
    if not isinstance(span, int):
        span = None

    kw = str(entities.get("calendar_keyword") or "").strip()
    if act == "list" and kw:
        act = "search"

    per = str(entities.get("calendar_period") or "full").lower()
    if per not in ("full", "morning", "afternoon"):
        per = "full"
    period: Period = per  # type: ignore[assignment]

    on_date: date | None = None
    od = entities.get("calendar_on_date")
    if isinstance(od, date):
        on_date = od
    elif isinstance(od, str) and od:
        try:
            parts = od.split("-")
            if len(parts) == 3:
                on_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            on_date = None

    return CalendarReadRequest(
        action=act,  # type: ignore[arg-type]
        window=window,
        span_days=span,
        keyword=kw,
        period=period,
        on_date=on_date,
    )


def request_from_router_intent(intent: Any) -> CalendarReadRequest:
    """Build from `RouterIntent` (core.intent.router)."""
    d: dict[str, Any] = {
        "calendar_window": getattr(intent, "calendar_window", "") or "upcoming",
        "calendar_span_days": getattr(intent, "calendar_span_days", None),
        "calendar_keyword": getattr(intent, "calendar_keyword", "") or "",
        "calendar_period": getattr(intent, "calendar_period", "") or "full",
    }
    cod = str(getattr(intent, "calendar_on_date", "") or "").strip()
    if cod:
        d["calendar_on_date"] = cod
    return request_from_entities(intent.action, d)


def request_from_calendar_intent(ci: Any) -> CalendarReadRequest:
    """Build from `CalendarIntent` (skills.calendar.interpreter)."""
    return request_from_entities(
        getattr(ci, "action", "list"),
        {
            "calendar_window": getattr(ci, "window", None) or "upcoming",
            "calendar_span_days": getattr(ci, "span_days", None),
            "calendar_keyword": getattr(ci, "keyword", None) or "",
            "calendar_period": getattr(ci, "period", None) or "full",
        },
    )


def _day_bounds(d: date, tz: tzinfo) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
    return start, start + timedelta(days=1)


def _apply_period(day_start: datetime, period: Period) -> tuple[datetime, datetime]:
    if period == "morning":
        return (
            day_start.replace(hour=8, minute=0, second=0, microsecond=0),
            day_start.replace(hour=12, minute=0, second=0, microsecond=0),
        )
    if period == "afternoon":
        return (
            day_start.replace(hour=13, minute=0, second=0, microsecond=0),
            day_start.replace(hour=18, minute=0, second=0, microsecond=0),
        )
    return day_start, day_start + timedelta(days=1)


def _resolve_query_window(
    req: CalendarReadRequest,
    now_tz: datetime,
) -> tuple[datetime, datetime]:
    """Return [start, end) in the workdays timezone for querying the API."""
    tz = now_tz.tzinfo
    if tz is None:
        raise ValueError("now_tz must be timezone-aware")
    day0 = now_tz.replace(hour=0, minute=0, second=0, microsecond=0)

    if req.window == "on_date" and req.on_date is not None:
        start, end = _day_bounds(req.on_date, tz)
    elif req.window == "today":
        start, end = day0, day0 + timedelta(days=1)
    elif req.window == "tomorrow":
        d1 = day0 + timedelta(days=1)
        start, end = d1, d1 + timedelta(days=1)
    elif req.window == "week":
        n = max(1, req.span_days or 7)
        start, end = day0, day0 + timedelta(days=n)
    elif req.window == "days":
        n = max(1, req.span_days or 7)
        start, end = day0, day0 + timedelta(days=n)
    elif req.window == "upcoming":
        start, end = now_tz, now_tz + timedelta(days=14)
    else:
        start, end = now_tz, now_tz + timedelta(days=14)

    if req.period != "full" and req.window in ("today", "tomorrow", "on_date"):
        if req.window == "tomorrow":
            day_start = day0 + timedelta(days=1)
        elif req.window == "on_date" and req.on_date is not None:
            day_start, _ = _day_bounds(req.on_date, tz)
        else:
            day_start = day0
        p0, p1 = _apply_period(day_start, req.period)
        start = max(start, p0)
        end = min(end, p1)

    return start, end


def _merge_busy(events: list[Event]) -> list[tuple[datetime, datetime]]:
    if not events:
        return []
    intervals: list[tuple[datetime, datetime]] = []
    for e in events:
        s, en = e.start, e.end
        if s.tzinfo is None:
            s = s.replace(tzinfo=UTC)
        if en.tzinfo is None:
            en = en.replace(tzinfo=UTC)
        intervals.append((s, en))
    intervals.sort(key=lambda x: x[0])
    merged: list[tuple[datetime, datetime]] = []
    for s, en in intervals:
        if not merged or s > merged[-1][1]:
            merged.append((s, en))
        else:
            prev_s, prev_e = merged[-1]
            merged[-1] = (prev_s, max(prev_e, en))
    return merged


def _gaps_in_window(
    busy: list[tuple[datetime, datetime]],
    win_start: datetime,
    win_end: datetime,
) -> list[tuple[datetime, datetime]]:
    gaps: list[tuple[datetime, datetime]] = []
    cur = win_start
    for s, en in busy:
        if s > cur:
            gaps.append((cur, min(s, win_end)))
        cur = max(cur, en)
    if cur < win_end:
        gaps.append((cur, win_end))
    out: list[tuple[datetime, datetime]] = []
    for a, b in gaps:
        if (b - a).total_seconds() >= _MIN_GAP_MINUTES * 60:
            out.append((a, b))
    return out


def _format_ev_line(ev: Event, lang: str, tz: tzinfo) -> str:
    start = ev.start.astimezone(tz)
    start_s = start.strftime("%d/%m %H:%M")
    line = f"{start_s}  {ev.title}"
    if ev.location and len(ev.location) < 80:
        line += f"\n    {t('events.location', lang, location=ev.location)}"
    if ev.link:
        line += f"\n    {ev.link}"
    return line


def execute_calendar_read(
    *,
    tokens_dir: Path,
    data_dir: Path,
    user_message: str,
    lang: str,
    req: CalendarReadRequest,
) -> str:
    """Run the read and return user-facing text (translated where applicable)."""
    presence = load_presence(data_dir)
    profile = load_profile(data_dir)
    accounts = profile.best_calendar_accounts(user_message, presence.status)
    if not accounts:
        return t("blocking.no_account", lang)

    account = accounts[0]
    schedule = load_workdays(data_dir)
    tz_name = schedule.timezone
    try:
        tz: tzinfo = ZoneInfo(tz_name)
    except Exception:
        tz = UTC

    now_tz = datetime.now(tz)

    try:
        client = CalendarClient(account, tokens_dir)
    except CalendarError as e:
        return f"✗ {e}"

    if req.action == "free_busy":
        win_start, win_end = _resolve_query_window(req, now_tz)
        try:
            busy_events = client.list_in_window(win_start, win_end, "primary")
        except CalendarError as e:
            return f"✗ {e}"
        merged = _merge_busy(busy_events)
        gaps = _gaps_in_window(merged, win_start, win_end)
        if not gaps:
            return t("calendar.no_free_slot", lang)
        lines = [t("calendar.free_busy_header", lang)]
        for a, b in gaps[:12]:
            a_l = a.astimezone(tz).strftime("%d/%m %H:%M")
            b_l = b.astimezone(tz).strftime("%H:%M")
            lines.append(t("calendar.free_slot", lang, start=a_l, end=b_l))
        return "\n".join(lines)

    events: list[Event] = []
    try:
        if req.window != "upcoming" or req.keyword:
            win_start, win_end = _resolve_query_window(req, now_tz)
            if req.window == "week" and not req.keyword:
                events = client.list_next_days(days=max(1, req.span_days or 7))
            else:
                events = client.list_in_window(win_start, win_end, "primary")
        else:
            events = client.list_upcoming(max_results=20, calendar_id="primary")
    except CalendarError as e:
        return f"✗ {e}"

    if req.keyword and req.action in ("list", "search"):
        kw = req.keyword.lower()
        events = [
            e
            for e in events
            if kw in e.title.lower()
            or kw in (e.location or "").lower()
            or kw in (getattr(e, "description", "") or "").lower()
        ]

    if not events:
        return t("calendar.no_events", lang)

    lines_out = [_format_ev_line(e, lang, tz) for e in events[:25]]
    return "\n".join(lines_out)
