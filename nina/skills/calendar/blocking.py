"""Interpret free-text blocking requests and create calendar events."""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

# Layer 1 gate: require at least one time/scheduling signal before calling LLM.
# Without this, any unrecognized sentence gets turned into a calendar event.
_TIME_SIGNAL = re.compile(
    r"""
    \b(
        \d+\s*h\b               # "15h", "2h"
      | \d{1,2}:\d{2}           # "15:30", "8:00"
      | \d+\s*hora[s]?          # "1 hora", "2 horas"
      | \d+\s*minuto[s]?        # "30 minutos"
      | uma\s+hora              # "uma hora"
      | meia\s+hora             # "meia hora"
      | duas\s+horas?           # "duas horas"
      | tr[eê]s\s+horas?        # "três horas"
      | agora                   # "agora"
      | now\b                   # "now"
      | daqui\b                 # "daqui 15 minutos"
      | às\s+\d                 # "às 15"
      | at\s+\d                 # "at 3"
      | bloqueie?\b             # "bloqueie", "bloqueia"
      | agende?\b               # "agende", "agenda"
      | schedule\b              # "schedule"
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

def has_time_signal(text: str) -> bool:
    """Keyword gate — no LLM."""
    return bool(_TIME_SIGNAL.search(text))


from nina.core.llm.client import LLMClient
from nina.errors import CalendarError

_SYSTEM_PROMPT = """You are an assistant that interprets calendar blocking requests from natural language.

The current date and time will be provided as the first line of the user message in the format:
[now: YYYY-MM-DD HH:MM weekday]

Analyze the user's message and return a JSON array of events. Each event is an object with:
- "action": "block_calendar" if it describes blocking time in the calendar
- "title": descriptive event title summarizing what is happening (in the same language as the input)
- "duration_minutes": duration as an integer number of minutes (default 60 if not mentioned)
- "start_time": start time as "HH:MM" (24h). If no start time is given, use the current [now] time. If a relative offset is given (e.g. "daqui 15 minutos"), add it to [now].
- "date": the event date as "YYYY-MM-DD". Use [now] date for today/agora/current. For relative days ("segunda", "monday", "amanhã", "tomorrow") calculate the correct future date from [now].

Rules:
- A single message may contain MULTIPLE events — return one object per event
- If there are no blocking events at all, return an empty array []
- "uma hora" / "1 hora" / "one hour" = 60 minutes
- "meia hora" / "30 minutos" / "half an hour" = 30 minutes
- "duas horas" / "2 horas" / "two hours" = 120 minutes
- Always return start_time as "HH:MM" in 24-hour format
- "segunda"/"segunda-feira"/"monday" = next Monday from [now] date
- "terça"/"tuesday" = next Tuesday, etc.
- "amanhã"/"tomorrow" = [now] date + 1 day
- "hoje"/"today" = [now] date
- Extract the most meaningful title from the context (who, what activity)

Return ONLY valid JSON (an array), no explanation, no markdown.

Examples (assuming now is 2026-03-28 13:15 saturday):
"estou atendendo a professora Sandra Mariotto, devo levar uma hora"
-> [{"action": "block_calendar", "title": "Atendimento Sandra Mariotto", "duration_minutes": 60, "start_time": "13:15", "date": "2026-03-28"}]

"agende na segunda feira as 14:00 reunião com Rafael"
-> [{"action": "block_calendar", "title": "Reunião com Rafael", "duration_minutes": 60, "start_time": "14:00", "date": "2026-03-30"}]

"amanhã às 10:00 consulta médica 30 minutos"
-> [{"action": "block_calendar", "title": "Consulta médica", "duration_minutes": 30, "start_time": "10:00", "date": "2026-03-29"}]

"daqui 15 minutos começo uma consultoria de 2 horas"
-> [{"action": "block_calendar", "title": "Consultoria", "duration_minutes": 120, "start_time": "13:30", "date": "2026-03-28"}]

"Qual é o tempo hoje?"
-> []
"""


@dataclass
class BlockingIntent:
    action: str                  # "block_calendar" | "none"
    title: str = ""
    duration_minutes: int = 60
    start_time: str = ""         # HH:MM (24h); empty = use now in execute()
    date: str = ""               # YYYY-MM-DD; empty = use today in execute()


@dataclass
class BlockingResult:
    event_title: str
    start: datetime
    end: datetime
    conflicts: list[str]         # titles of overlapping events
    link: str = ""               # Google Calendar event URL


def interpret(text: str, llm: LLMClient, now: datetime | None = None) -> list[BlockingIntent]:
    """Parse *text* and return a list of BlockingIntents. Never raises."""
    if not _TIME_SIGNAL.search(text):
        return []
    if now is None:
        now = datetime.now()
    weekday = now.strftime("%A").lower()
    stamped = f"[now: {now.strftime('%Y-%m-%d %H:%M')} {weekday}]\n{text}"
    try:
        raw = llm.complete(stamped, system=_SYSTEM_PROMPT)
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(raw)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    results: list[BlockingIntent] = []
    for item in data:
        if not isinstance(item, dict) or item.get("action") != "block_calendar":
            continue
        try:
            title = str(item.get("title", "Bloqueado"))
            duration = max(1, int(item.get("duration_minutes", 60)))
            start_time_str = str(item.get("start_time", now.strftime("%H:%M")))
            sh, sm = (int(x) for x in start_time_str.split(":"))
            if not (0 <= sh <= 23 and 0 <= sm <= 59):
                continue
            date_str = str(item.get("date", now.strftime("%Y-%m-%d")))
        except (ValueError, TypeError, AttributeError):
            continue
        results.append(BlockingIntent(
            action="block_calendar",
            title=title,
            duration_minutes=duration,
            start_time=f"{sh:02d}:{sm:02d}",
            date=date_str,
        ))

    return results


def execute(
    intent: BlockingIntent,
    account: str,
    tokens_dir,
    tz_name: str = "America/Cuiaba",
    calendar_id: str = "primary",
) -> BlockingResult:
    """Create the blocking event and return a BlockingResult with any conflicts."""
    from zoneinfo import ZoneInfo

    from nina.integrations.google.calendar.client import CalendarClient

    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    if intent.start_time:
        sh, sm = (int(x) for x in intent.start_time.split(":"))
        base = now
        if intent.date:
            y, mo, d = (int(x) for x in intent.date.split("-"))
            base = now.replace(year=y, month=mo, day=d)
        raw_start = base.replace(hour=sh, minute=sm, second=0, microsecond=0)
    else:
        raw_start = now

    # Round start DOWN to the nearest 15-minute block
    start_remainder = raw_start.minute % 15
    start = (raw_start - timedelta(minutes=start_remainder)).replace(second=0, microsecond=0)

    # End is computed from the ORIGINAL (unrounded) start so the full duration is covered
    raw_end = raw_start + timedelta(minutes=intent.duration_minutes)

    # Round end UP to the next 15-minute block
    remainder = raw_end.minute % 15
    if remainder != 0:
        raw_end = raw_end + timedelta(minutes=15 - remainder)
    end = raw_end.replace(second=0, microsecond=0)

    client = CalendarClient(account, tokens_dir)

    # Check for conflicts before creating
    try:
        overlapping = client.list_in_window(start, end, calendar_id)
        conflicts = [e.title for e in overlapping]
    except CalendarError:
        conflicts = []

    # Create the blocking event
    event = client.create_event(
        title=intent.title,
        start=start,
        end=end,
        calendar_id=calendar_id,
    )

    return BlockingResult(
        event_title=event.title,
        start=start,
        end=end,
        conflicts=conflicts,
        link=event.link,
    )
