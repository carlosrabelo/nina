# nina/obsidian/week_page.py
"""Renders week.md — 7-day agenda grouped by day, with due memos."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from nina.store.repos import memo as memo_repo

_DAY_NAMES_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DAY_NAMES_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def render(
    conn: sqlite3.Connection,
    accounts: list[str],
    tokens_dir: Path,
    timezone_name: str = "UTC",
    lang: str = "en",
) -> str:
    """Return the full markdown content for week.md."""
    from nina.errors import CalendarError
    from nina.google.calendar.client import CalendarClient

    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    if lang == "pt":
        start_str = week_start.strftime("%d/%m")
        end_str = (week_end - timedelta(days=1)).strftime("%d/%m")
        title = f"# Semana — {start_str} – {end_str}"
        no_events = "_Nenhum evento._"
        due_section = "## Memos com prazo"
        overdue_label = "⚠️ Vencido"
        due_label = "Vence"
        no_due = "_Nenhum memo com prazo nesta semana._"
        all_day = "Dia todo"
        day_names = _DAY_NAMES_PT
    else:
        start_str = week_start.strftime("%B %d")
        end_str = (week_end - timedelta(days=1)).strftime("%B %d")
        title = f"# Week — {start_str} – {end_str}"
        no_events = "_No events._"
        due_section = "## Memos due this week"
        overdue_label = "⚠️ Overdue"
        due_label = "Due"
        no_due = "_No memos due this week._"
        all_day = "All day"
        day_names = _DAY_NAMES_EN

    # ── fetch all events for the week in one pass per account ─────────────────
    all_events: list = []
    for account in accounts:
        try:
            client = CalendarClient(account, tokens_dir)
            all_events.extend(client.list_in_window(week_start, week_end))
        except CalendarError:
            continue

    # deduplicate by event_id
    seen: set[str] = set()
    unique_events = []
    for ev in sorted(all_events, key=lambda e: e.start):
        if ev.event_id not in seen:
            seen.add(ev.event_id)
            unique_events.append(ev)

    # group by day (0 = today, 6 = today+6)
    days: list[list] = [[] for _ in range(7)]
    for ev in unique_events:
        ev_local = ev.start.astimezone(tz)
        delta = (ev_local.date() - week_start.date()).days
        if 0 <= delta < 7:
            days[delta].append(ev)

    # ── render ────────────────────────────────────────────────────────────────
    lines = [title, ""]

    for i in range(7):
        day_date = week_start + timedelta(days=i)
        day_name = day_names[day_date.weekday()]
        if lang == "pt":
            header = f"## {day_name}, {day_date.strftime('%d/%m')}"
        else:
            header = f"## {day_name}, {day_date.strftime('%B %d')}"
        lines += [header, ""]

        if not days[i]:
            lines += [no_events, ""]
        else:
            for ev in days[i]:
                start_str_ev = ev.start.astimezone(tz).strftime("%H:%M")
                end_str_ev = ev.end.astimezone(tz).strftime("%H:%M")
                ev_local_start = ev.start.astimezone(tz)
                ev_local_end = ev.end.astimezone(tz)
                if ev_local_start.hour == 0 and ev_local_start.minute == 0 and ev_local_end.hour == 0:
                    time_str = all_day
                else:
                    time_str = f"{start_str_ev} → {end_str_ev}"
                location = f" · 📍 {ev.location}" if ev.location else ""
                lines.append(f"- **{time_str}** {ev.title}{location}")
            lines.append("")

    # ── memos with due dates ───────────────────────────────────────────────────
    lines += [due_section, ""]
    open_memos = memo_repo.list_open(conn)
    today_str = week_start.strftime("%Y-%m-%d")
    end_str_date = (week_end - timedelta(days=1)).strftime("%Y-%m-%d")

    overdue = [m for m in open_memos if m.due_date and m.due_date < today_str]
    due_this_week = [m for m in open_memos if m.due_date and today_str <= m.due_date <= end_str_date]

    if not overdue and not due_this_week:
        lines += [no_due, ""]
    else:
        for m in sorted(overdue, key=lambda m: m.due_date or ""):
            source_tag = " 🎤" if m.source == "voice" else ""
            lines.append(f"- [ ] {m.text}{source_tag} `{m.id[:8]}` — {overdue_label}: {m.due_date}")
        for m in sorted(due_this_week, key=lambda m: m.due_date or ""):
            source_tag = " 🎤" if m.source == "voice" else ""
            lines.append(f"- [ ] {m.text}{source_tag} `{m.id[:8]}` — {due_label}: {m.due_date}")
        lines.append("")

    return "\n".join(lines)
