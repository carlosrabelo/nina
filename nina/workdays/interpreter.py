"""Interpret free-text messages and extract workday schedule changes using the LLM."""

import json
import re
from dataclasses import dataclass
from datetime import time

from nina.llm.client import LLMClient
from nina.workdays.models import WorkSchedule

_KEYWORDS: dict[str, set[str]] = {
    "pt": {"segunda", "terça", "terca", "quarta", "quinta", "sexta",
           "sábado", "sabado", "domingo", "horário", "horario",
           "timezone", "fuso", "trabalho", "trabalhar"},
    "en": {"monday", "tuesday", "wednesday", "thursday", "friday",
           "saturday", "sunday", "schedule", "timezone", "work"},
}


def has_context(text: str, lang: str = "pt") -> bool:
    """Keyword gate — no LLM."""
    lower = text.lower()
    return any(kw in lower for kw in _KEYWORDS.get(lang, _KEYWORDS["pt"]))


_SYSTEM_PROMPT = """You are an assistant that interprets work schedule changes from natural language messages.

Days of the week are numbered 0 (Monday) to 6 (Sunday).

Analyze the user's message and return a JSON object with:
- "action": "update_schedule" if the message clearly describes a schedule change or timezone change, otherwise "none"
- "timezone": an IANA timezone string if the message mentions a timezone (e.g. "America/Cuiaba"), otherwise null
- "changes": a list of day changes (empty list if only timezone is changing)

Each change in the list has:
- "day": integer 0–6 (0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday)
- "active": true or false
- "start": "HH:MM" string or null (only when active is true)
- "end": "HH:MM" string or null (only when active is true)

Rules:
- If the message changes all working days uniformly, repeat the same change for each affected day.
- If the message only changes start or end time for specific days, include only those days.
- If the message says "I don't work on X", set active=false for that day (no start/end needed).
- Always use 24-hour format for times.
- If a start or end time is not mentioned for an active day, use null.

Return ONLY valid JSON, no explanation, no markdown.

Examples:
"Meu fuso horário é America/Cuiaba"
-> {"action": "update_schedule", "timezone": "America/Cuiaba", "changes": []}

"Meu horário é de Brasília"
-> {"action": "update_schedule", "timezone": "America/Sao_Paulo", "changes": []}

"Trabalho de segunda a sexta das 9 às 18"
-> {"action": "update_schedule", "timezone": null, "changes": [
     {"day": 0, "active": true, "start": "09:00", "end": "18:00"},
     {"day": 1, "active": true, "start": "09:00", "end": "18:00"},
     {"day": 2, "active": true, "start": "09:00", "end": "18:00"},
     {"day": 3, "active": true, "start": "09:00", "end": "18:00"},
     {"day": 4, "active": true, "start": "09:00", "end": "18:00"}
   ]}

"Sexta-feira eu saio às 17"
-> {"action": "update_schedule", "changes": [
     {"day": 4, "active": true, "start": null, "end": "17:00"}
   ]}

"Não trabalho às quartas"
-> {"action": "update_schedule", "changes": [
     {"day": 2, "active": false, "start": null, "end": null}
   ]}

"Meu horário começa às 8h30"
-> {"action": "update_schedule", "changes": [
     {"day": 0, "active": true, "start": "08:30", "end": null},
     {"day": 1, "active": true, "start": "08:30", "end": null},
     {"day": 2, "active": true, "start": "08:30", "end": null},
     {"day": 3, "active": true, "start": "08:30", "end": null},
     {"day": 4, "active": true, "start": "08:30", "end": null}
   ]}

"I work Monday to Thursday from 8 to 17, Fridays until 13"
-> {"action": "update_schedule", "changes": [
     {"day": 0, "active": true, "start": "08:00", "end": "17:00"},
     {"day": 1, "active": true, "start": "08:00", "end": "17:00"},
     {"day": 2, "active": true, "start": "08:00", "end": "17:00"},
     {"day": 3, "active": true, "start": "08:00", "end": "17:00"},
     {"day": 4, "active": true, "start": "08:00", "end": "13:00"}
   ]}

"Qual é o tempo hoje?"
-> {"action": "none"}
"""


@dataclass
class ScheduleChange:
    day: int
    active: bool
    start: time | None
    end: time | None


@dataclass
class ScheduleIntent:
    action: str                        # "update_schedule" | "none"
    changes: list[ScheduleChange]
    timezone: str | None = None


def interpret(text: str, llm: LLMClient) -> ScheduleIntent:
    """Parse *text* and return a ScheduleIntent. Never raises — returns action=none on any error."""
    try:
        raw = llm.complete(text, system=_SYSTEM_PROMPT)
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(raw)
    except Exception:
        return ScheduleIntent(action="none", changes=[])

    if data.get("action") != "update_schedule":
        return ScheduleIntent(action="none", changes=[])

    # Validate timezone if provided
    timezone: str | None = None
    if tz_raw := data.get("timezone"):
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(tz_raw)
            timezone = tz_raw
        except Exception:
            pass

    changes: list[ScheduleChange] = []
    for item in data.get("changes", []):
        try:
            day = int(item["day"])
            if day < 0 or day > 6:
                continue
            active = bool(item["active"])
            start = time.fromisoformat(item["start"]) if item.get("start") else None
            end = time.fromisoformat(item["end"]) if item.get("end") else None
            changes.append(ScheduleChange(day=day, active=active, start=start, end=end))
        except (KeyError, ValueError):
            continue

    if not changes and timezone is None:
        return ScheduleIntent(action="none", changes=[])

    return ScheduleIntent(action="update_schedule", changes=changes, timezone=timezone)


def apply(intent: ScheduleIntent, schedule: WorkSchedule) -> WorkSchedule:
    """Apply a ScheduleIntent to an existing WorkSchedule and return it (mutated in place)."""
    if intent.timezone:
        schedule.timezone = intent.timezone
    for change in intent.changes:
        for wd in schedule.days:
            if wd.day == change.day:
                wd.active = change.active
                if change.start is not None:
                    wd.start = change.start
                if change.end is not None:
                    wd.end = change.end
                if not change.active:
                    wd.start = None
                    wd.end = None
                break
    return schedule
