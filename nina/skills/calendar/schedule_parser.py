"""Parse structured schedule commands without LLM.

Accepted formats:
    schedule HH:MM <title> [duration]
    schedule today HH:MM <title> [duration]
    schedule tomorrow HH:MM <title> [duration]
    schedule DD/MM HH:MM <title> [duration]
    schedule DD/MM/YYYY HH:MM <title> [duration]

Duration suffixes (optional, default 60min):
    1h  30min  1h30  1h30min  90min
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass
class ScheduleParseResult:
    start: datetime
    duration_minutes: int
    title: str


_DURATION_RE = re.compile(
    r"^(?:(\d+)h(\d+)(?:min)?|(\d+)h|(\d+)min)$",
    re.IGNORECASE,
)
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$")

_TODAY_WORDS = {"hoje", "today"}
_TOMORROW_WORDS = {"amanhã", "amanha", "tomorrow"}


def _parse_duration(token: str) -> int | None:
    m = _DURATION_RE.match(token)
    if not m:
        return None
    if m.group(1) is not None:      # XhY / XhYmin
        return int(m.group(1)) * 60 + int(m.group(2))
    if m.group(3) is not None:      # Xh
        return int(m.group(3)) * 60
    if m.group(4) is not None:      # Xmin
        return int(m.group(4))
    return None


def parse(text: str, now: datetime) -> ScheduleParseResult | None:
    """Return a ScheduleParseResult or None if the text cannot be parsed."""
    tokens = text.strip().split()
    if not tokens:
        return None

    idx = 0
    target_date: date = now.date()

    # 1. Optional date token
    first = tokens[0].lower()
    if first in _TODAY_WORDS:
        idx = 1
    elif first in _TOMORROW_WORDS:
        target_date = now.date() + timedelta(days=1)
        idx = 1
    elif _DATE_RE.match(tokens[0]):
        m = _DATE_RE.match(tokens[0])
        assert m
        day, month = int(m.group(1)), int(m.group(2))
        year = now.year
        if m.group(3):
            year = int(m.group(3))
            if year < 100:
                year += 2000
        try:
            target_date = date(year, month, day)
        except ValueError:
            return None
        idx = 1

    # 2. Required HH:MM
    if idx >= len(tokens):
        return None
    tm = _TIME_RE.match(tokens[idx])
    if not tm:
        return None
    hour, minute = int(tm.group(1)), int(tm.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    idx += 1

    # 3. Remaining tokens = [title words...] [duration?]
    rest = tokens[idx:]
    if not rest:
        return None

    duration = 60
    dur = _parse_duration(rest[-1])
    if dur is not None:
        duration = max(1, dur)
        rest = rest[:-1]

    if not rest:
        return None

    title = " ".join(rest)
    start = datetime(
        target_date.year, target_date.month, target_date.day,
        hour, minute, 0,
        tzinfo=now.tzinfo,
    )
    return ScheduleParseResult(start=start, duration_minutes=duration, title=title)
