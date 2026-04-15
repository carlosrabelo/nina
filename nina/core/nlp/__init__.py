"""Local NLP utilities — date/time resolution, keyword extraction, entity parsing.

No LLM calls — pure regex and dictionary-based parsing for PT/EN.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

# ── Weekday mappings ─────────────────────────────────────────────────────────

_WEEKDAYS_PT = [
    "segunda",
    "terça",
    "terca",
    "quarta",
    "quinta",
    "sexta",
    "sábado",
    "sabado",
    "domingo",
]
_WEEKDAYS_EN = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
_ALL_WEEKDAYS = _WEEKDAYS_PT + _WEEKDAYS_EN

# ── Time expression patterns ─────────────────────────────────────────────────

# "às 14h", "as 14h", "at 14:00", "14h30", "14:00", "das 9 às 18"
_TIME_RE = re.compile(
    r"(?:[àa]s\s+)?(\d{1,2})[h:](\d{2})?",
    re.IGNORECASE,
)
_DURATION_RE = re.compile(
    r"(?:por\s+)?(\d+)\s*(?:h(?:ora[s]?)?|min(?:uto[s]?)?)",
    re.IGNORECASE,
)

# ── Date expression patterns ─────────────────────────────────────────────────

_DATE_WORDS_PT: dict[str, int] = {
    "hoje": 0,
    "amanhã": 1,
    "amanha": 1,
    "depois": 2,
}
_DATE_WORDS_EN: dict[str, int] = {
    "today": 0,
    "tomorrow": 1,
}

# "próxima segunda", "next monday", "segunda que vem"
_NEXT_WEEKDAY_PT = re.compile(
    r"(?:pr[oó]xim[ao]|que\s+vem)\s+(segunda|ter[çc]a|quarta|quinta|sexta|s[áa]bado|domingo)",
    re.IGNORECASE,
)
_NEXT_WEEKDAY_EN = re.compile(
    r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
    re.IGNORECASE,
)

# DD/MM or DD/MM/YYYY
_DATE_NUMERIC = re.compile(
    r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?",
)


@dataclass
class TimeEntity:
    hour: int
    minute: int


@dataclass
class DateEntity:
    date: date


@dataclass
class DurationEntity:
    minutes: int


def parse_time(text: str) -> TimeEntity | None:
    """Extract a time like '14h', '14:30', 'às 9h' from text."""
    m = _TIME_RE.search(text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return TimeEntity(hour=hour, minute=minute)
    return None


def parse_duration(text: str) -> DurationEntity | None:
    """Extract a duration like 'por 1 hora', '30min', '1h30'."""
    # "1h30" format
    m_hm = re.search(r"(\d+)h(\d+)", text)
    if m_hm:
        return DurationEntity(minutes=int(m_hm.group(1)) * 60 + int(m_hm.group(2)))

    m = _DURATION_RE.search(text)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(0).lower()
    if "min" in unit:
        return DurationEntity(minutes=val)
    # hours
    return DurationEntity(minutes=val * 60)


def parse_date_relative(text: str, now: datetime | None = None) -> DateEntity | None:
    """Resolve date words like 'hoje', 'amanhã', 'próxima segunda'."""
    if now is None:
        now = datetime.now()
    base = now.date()

    # "hoje", "amanhã"
    for word, offset in _DATE_WORDS_PT.items():
        if word in text.lower():
            return DateEntity(date=base + timedelta(days=offset))
    for word, offset in _DATE_WORDS_EN.items():
        if word in text.lower():
            return DateEntity(date=base + timedelta(days=offset))

    # "próxima segunda"
    m = _NEXT_WEEKDAY_PT.search(text)
    if m:
        return DateEntity(date=_resolve_weekday(m.group(1).lower(), _WEEKDAYS_PT, now))

    m = _NEXT_WEEKDAY_EN.search(text)
    if m:
        return DateEntity(date=_resolve_weekday(m.group(1).lower(), _WEEKDAYS_EN, now))

    # DD/MM
    m = _DATE_NUMERIC.search(text)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = now.year
        if m.group(3):
            year = int(m.group(3))
            if year < 100:
                year += 2000
        try:
            return DateEntity(date=date(year, month, day))
        except ValueError:
            pass
    return None


def _resolve_weekday(name: str, weekday_list: list[str], now: datetime) -> date:
    """Return the date of the next occurrence of the given weekday."""
    # Normalize: remove accents for matching
    target_idx = weekday_list.index(name) % 7
    today_idx = now.weekday()  # Monday=0
    days_ahead = target_idx - today_idx
    if days_ahead <= 0:
        days_ahead += 7
    return now.date() + timedelta(days=days_ahead)


def parse_date_number(text: str) -> int | None:
    """Extract a plain number from text (for reminder minutes, watch days)."""
    m = re.search(r"\b(\d+)\b", text)
    if m:
        return int(m.group(1))
    return None
