"""Query past activity entries from Google Calendar."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from nina.errors import CalendarError
from nina.skills.activity_log.models import ActivityEntry, ActivitySummary


def query_activities(
    account: str,
    tokens_dir: Path,
    tz_name: str = "America/Cuiaba",
    calendar_id: str = "primary",
    target_date: date | None = None,
    keyword: str = "",
) -> list[ActivityEntry]:
    """Query past events from Google Calendar for a given date or keyword."""
    from zoneinfo import ZoneInfo

    from nina.integrations.google.calendar.client import CalendarClient

    tz = ZoneInfo(tz_name)

    if target_date:
        start = datetime(target_date.year, target_date.month, target_date.day,
                         0, 0, tzinfo=tz)
        end = start + timedelta(days=1)
    else:
        # Default: last 7 days
        now = datetime.now(tz)
        start = now - timedelta(days=7)
        end = now

    try:
        client = CalendarClient(account, tokens_dir)
        events = client.list_in_window(start, end, calendar_id)
    except CalendarError:
        return []

    # Filter by keyword if provided
    if keyword:
        kw_lower = keyword.lower()
        events = [e for e in events if kw_lower in e.title.lower()
                  or kw_lower in (e.description or "").lower()]

    # Only include events that have "Nina" in description (activity log entries)
    # OR all events if we're querying general calendar data
    entries: list[ActivityEntry] = []
    for ev in events:
        entries.append(ActivityEntry(
            title=ev.title,
            start=ev.start,
            end=ev.end,
            account=ev.account,
            calendar=ev.calendar,
            link=ev.link,
            description=ev.description if hasattr(ev, 'description') else "",
        ))

    return entries


def get_summary(
    account: str,
    tokens_dir: Path,
    tz_name: str = "America/Cuiaba",
    calendar_id: str = "primary",
    week_start: date | None = None,
) -> ActivitySummary:
    """Get a summary of activities for a given week."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    if week_start is None:
        # Current week's Monday
        week_start = now.date() - timedelta(days=now.weekday())

    week_end = week_start + timedelta(days=7)

    entries = query_activities(
        account, tokens_dir, tz_name, calendar_id,
    )

    # Filter to the week
    week_entries = [
        e for e in entries if week_start <= e.start.date() < week_end
    ]
    total_minutes = sum(
        int((e.end - e.start).total_seconds() / 60) for e in week_entries
    )

    # Group by keyword (first word of title)
    by_keyword: dict[str, int] = {}
    for e in week_entries:
        kw = e.title.split()[0].lower() if e.title else "unknown"
        minutes = int((e.end - e.start).total_seconds() / 60)
        by_keyword[kw] = by_keyword.get(kw, 0) + minutes

    start_label = week_start.strftime("%d/%m")
    end_label = (week_start + timedelta(days=6)).strftime("%d/%m")

    return ActivitySummary(
        period_label=f"Semana {start_label} → {end_label}",
        total_minutes=total_minutes,
        entries=week_entries,
        by_keyword=by_keyword,
    )


def query_by_keyword(
    account: str,
    tokens_dir: Path,
    keyword: str,
    tz_name: str = "America/Cuiaba",
    calendar_id: str = "primary",
    days_back: int = 30,
) -> list[ActivityEntry]:
    """Search for activities by keyword across a time window."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    start = now - timedelta(days=days_back)

    try:
        from nina.integrations.google.calendar.client import CalendarClient
        client = CalendarClient(account, tokens_dir)
        events = client.list_in_window(start, now, calendar_id)
    except CalendarError:
        return []

    kw_lower = keyword.lower()
    return [
        ActivityEntry(
            title=ev.title,
            start=ev.start,
            end=ev.end,
            account=ev.account,
            calendar=ev.calendar,
            link=ev.link,
        )
        for ev in events
        if kw_lower in ev.title.lower() or kw_lower in (ev.description or "").lower()
    ]
