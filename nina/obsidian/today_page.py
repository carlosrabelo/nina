# nina/obsidian/today_page.py
"""Renders today.md — daily briefing with agenda and open memos."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from nina.store.repos import memo as memo_repo


def render(
    conn: sqlite3.Connection,
    accounts: list[str],
    tokens_dir: Path,
    timezone_name: str = "UTC",
    lang: str = "en",
) -> str:
    """Return the full markdown content for today.md."""
    from nina.errors import CalendarError
    from nina.google.calendar.client import CalendarClient

    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    date_str = now.strftime("%A, %B %d %Y") if lang == "en" else now.strftime("%d/%m/%Y")

    if lang == "pt":
        title = f"# Hoje — {date_str}"
        agenda_section = "## Agenda"
        memos_section = "## Memos abertos"
        no_events = "_Nenhum evento hoje._"
        no_memos = "_Nenhum memo aberto._"
        due_label = "Vence"
        all_day = "Dia todo"
    else:
        title = f"# Today — {date_str}"
        agenda_section = "## Agenda"
        memos_section = "## Open memos"
        no_events = "_No events today._"
        no_memos = "_No open memos._"
        due_label = "Due"
        all_day = "All day"

    lines = [title, ""]

    # ── Agenda ────────────────────────────────────────────────────────────────
    lines += [agenda_section, ""]

    events_today: list = []
    for account in accounts:
        try:
            client = CalendarClient(account, tokens_dir)
            events = client.list_in_window(today_start, today_end)
            events_today.extend(events)
        except CalendarError:
            continue

    # Deduplicate by event_id, sort by start time
    seen: set[str] = set()
    unique_events = []
    for ev in sorted(events_today, key=lambda e: e.start):
        if ev.event_id not in seen:
            seen.add(ev.event_id)
            unique_events.append(ev)

    if not unique_events:
        lines += [no_events, ""]
    else:
        for ev in unique_events:
            start_str = ev.start.strftime("%H:%M")
            end_str = ev.end.strftime("%H:%M")
            # All-day events have midnight UTC start
            if ev.start.hour == 0 and ev.start.minute == 0 and ev.end.hour == 0:
                time_str = all_day
            else:
                time_str = f"{start_str} → {end_str}"
            location = f" · 📍 {ev.location}" if ev.location else ""
            lines.append(f"- **{time_str}** {ev.title}{location}")
        lines.append("")

    # ── Open memos ────────────────────────────────────────────────────────────
    lines += [memos_section, ""]
    memos = memo_repo.list_open(conn)
    if not memos:
        lines += [no_memos, ""]
    else:
        for m in memos:
            due = f" — {due_label}: {m.due_date}" if m.due_date else ""
            source_tag = " 🎤" if m.source == "voice" else ""
            short_id = m.id[:8]
            lines.append(f"- [ ] {m.text}{due}{source_tag} `{short_id}`")
        lines.append("")

    return "\n".join(lines)
