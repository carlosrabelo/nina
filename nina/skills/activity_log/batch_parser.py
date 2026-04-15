"""Batch activity parser — extract multiple activities from one message.

Example input:
    "reunião com cliente 9h às 10h, deploy da Nina 10h-12h, code review à tarde"

Returns a list of ActivityIntent, one per activity.
"""

from __future__ import annotations

import re
from datetime import datetime

from nina.skills.activity_log.models import ActivityIntent
from nina.skills.activity_log.patterns import (
    _parse_date,
    _parse_duration,
    _parse_time_range,
)

# Split by comma, "e", "também", or newline
_SPLIT_RE = re.compile(r"\s*(?:,|\s+e\s+|\s+também\s+|\n)\s*", re.I)

# Extract time reference from a fragment
_FRAG_TIME_RE = re.compile(
    r"(?:das?\s+)?(\d{1,2})[h:](\d{2})?"
    r"(?:\s*[àa]s?\s*(\d{1,2})[h:](\d{2})?)?",
    re.I,
)

# Duration in fragment
_FRAG_DURATION_RE = re.compile(r"(\d+)h(\d+)?(?:min)?|\bpor\s+(\d+)\s*(h|min)", re.I)


def parse_batch(text: str, lang: str = "pt", now: datetime | None = None) -> list[ActivityIntent]:
    """Parse a multi-activity message into individual ActivityIntents."""
    if now is None:
        now = datetime.now()

    # Split into fragments
    fragments = _SPLIT_RE.split(text.strip())
    fragments = [f.strip() for f in fragments if f.strip()]

    if not fragments:
        return []

    intents: list[ActivityIntent] = []
    for frag in fragments:
        intent = _parse_fragment(frag, lang, now)
        if intent and intent.action == "log":
            intents.append(intent)

    return intents


def _parse_fragment(text: str, lang: str, now: datetime) -> ActivityIntent | None:
    """Parse a single activity fragment."""
    if len(text) < 3:
        return None

    intent = ActivityIntent(action="log", title=text.strip())

    # Extract title (remove time refs)
    title = _clean_title(text)
    if title:
        intent.title = title

    # Extract time range
    time_range = _parse_time_range(text)
    if time_range:
        sh, sm, eh, em = time_range
        base_date = _parse_date(text, now) or now.date()
        from datetime import datetime as dt
        intent.start = dt(base_date.year, base_date.month, base_date.day, sh, sm)
        intent.end = dt(base_date.year, base_date.month, base_date.day, eh, em)
        intent.duration_minutes = (eh * 60 + em) - (sh * 60 + sm)
        if intent.duration_minutes <= 0:
            intent.duration_minutes += 24 * 60
    else:
        # Try single time + duration
        m = _FRAG_TIME_RE.search(text)
        if m:
            sh = int(m.group(1))
            sm = int(m.group(2)) if m.group(2) else 0
            base_date = _parse_date(text, now) or now.date()
            from datetime import datetime as dt
            from datetime import timedelta
            intent.start = dt(base_date.year, base_date.month, base_date.day, sh, sm)
            dur = _extract_duration(text)
            intent.duration_minutes = dur or 60
            intent.end = intent.start + timedelta(minutes=intent.duration_minutes)
        else:
            # No time — default 60 min
            dur = _extract_duration(text)
            intent.duration_minutes = dur or 60

    # Date reference
    target_date = _parse_date(text, now)
    if target_date:
        intent.target_date = target_date

    return intent


def _clean_title(text: str) -> str:
    """Remove time/date references to get clean activity title."""
    # Remove time ranges: "das 14h às 15h30", "9h-12h"
    title = re.sub(r"\b(das?|de)\s+\d+[h:]\d{0,2}\s+[àa]s?\s+\d+[h:]\d{0,2}\b", "", text, flags=re.I)
    title = re.sub(r"\b\d+[h:]\d{0,2}\s*[-–]\s*\d+[h:]\d{0,2}\b", "", title, flags=re.I)
    # Remove duration: "por 1h", "por 30min"
    title = re.sub(r"\bpor\s+\d+\s*(h|min)\b", "", title, flags=re.I)
    title = re.sub(r"\b\d+h\d*(?:min)?\b", "", title, flags=re.I)
    # Remove date words
    for word in ["hoje", "ontem", "anteontem", "amanhã"]:
        title = re.sub(rf"\b{re.escape(word)}\b", "", title, flags=re.I)
    # Clean up
    title = title.strip().strip(" -,")
    if title:
        return title[0].upper() + title[1:]
    return text.strip()


def _extract_duration(text: str) -> int:
    """Extract duration in minutes from text."""
    dur = _parse_duration(text)
    if dur > 0:
        return dur
    m = _FRAG_DURATION_RE.search(text)
    if m:
        if m.group(1):
            hours = int(m.group(1))
            mins = int(m.group(2)) if m.group(2) else 0
            return hours * 60 + mins
        val = int(m.group(3))
        unit = m.group(4).lower() if m.group(4) else "h"
        if "min" in unit:
            return val
        return val * 60
    return 0
