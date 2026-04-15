"""Activity log interpreter — local patterns first, LLM fallback."""

# ruff: noqa: E501 — _SYSTEM_PROMPT lines are LLM prompts, not code

from __future__ import annotations

import json
import re
from datetime import datetime

from nina.core.llm.client import LLMClient
from nina.skills.activity_log.models import ActivityIntent
from nina.skills.activity_log.patterns import (
    _DATE_WORDS_EN,
    _DATE_WORDS_PT,
    _LOG_NOUNS,
    _LOG_VERBS_EN,
    _LOG_VERBS_PT,
    _QUERY_PATTERNS,
    _WEEKDAYS_EN,
    _WEEKDAYS_PT,
    _parse_date,
    _parse_duration,
    _parse_time_range,
    has_activity_log_signal,
)

# ── Title extraction ─────────────────────────────────────────────────────────

# Remove filler words to get clean title
_FILLER_PT = {
    "fiz", "criei", "montei", "implementei", "terminei", "completei",
    "estive", "estou", "em", "no", "na", "por", "para", "com", "uma", "um",
    "que", "o", "a", "os", "as", "do", "da", "dos", "das",
}
_FILLER_EN = {
    "did", "created", "built", "implemented", "finished", "completed",
    "was", "in", "at", "the", "for", "with", "a", "an",
}


def _extract_title(text: str, lang: str = "pt") -> str:
    """Extract a clean activity title from text."""
    lower = text.lower()
    # Remove time range: "das 14h às 15h30"
    title = re.sub(r"(?:das|de|from)\s+\d+[h:]\d{0,2}\s+[àa]s?\s+\d+[h:]\d{0,2}", "", lower, flags=re.I)
    # Remove duration: "por 1h", "por 30min"
    title = re.sub(r"\s+por\s+\d+\s*h(?:ora[s]?)?", "", title, flags=re.I)
    title = re.sub(r"\s+por\s+\d+\s*min(?:uto[s]?)?", "", title, flags=re.I)
    title = re.sub(r"\s+\d+h\d+(?:min)?\b", "", title, flags=re.I)
    # Remove date words
    for w in list(_DATE_WORDS_PT) + list(_DATE_WORDS_EN):
        title = re.sub(rf"\b{re.escape(w)}\b", "", title, flags=re.I)
    for w in _WEEKDAYS_PT + _WEEKDAYS_EN:
        title = re.sub(rf"\b{re.escape(w)}\b", "", title, flags=re.I)
    # Remove "na", "no", "semana passada"
    title = re.sub(r"\b(na|no|semana\s+passada|last\s+week)\b", "", title, flags=re.I)

    # Capitalize and clean
    title = title.strip().strip(" -")
    if title:
        return title[0].upper() + title[1:]
    return text.strip()


# ── LLM system prompt ────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an assistant that interprets activity logging requests.
The user wants to log past work activities to their calendar.
If provided, the first line is [now: YYYY-MM-DD HH:MM weekday].
Return ONLY a JSON object — no explanation, no markdown.

Schema for logging:
{
  "action": "log",
  "title": "<activity description>",
  "duration_minutes": <int, default 60>,
  "start": "<HH:MM or null>",
  "end": "<HH:MM or null>",
  "date": "<YYYY-MM-DD or null for today>"
}

Schema for querying:
{
  "action": "query",
  "query_type": "day|week|keyword",
  "date": "<YYYY-MM-DD for day, Monday of week for week>",
  "keyword": "<search keyword or empty string>"
}

Schema for summary:
{
  "action": "summary",
  "query_type": "week|day",
  "date": "<YYYY-MM-DD>"
}

Examples:
"fiz deploy da feature X ontem"
→ {"action": "log", "title": "Deploy feature X", "duration_minutes": 60, "start": null, "end": null, "date": "2026-04-10"}

"estive em reunião com time backend por 1h"
→ {"action": "log", "title": "Reunião com time backend", "duration_minutes": 60, "start": null, "end": null, "date": null}

"reunião com cliente das 14h às 15h30"
→ {"action": "log", "title": "Reunião com cliente", "duration_minutes": 90, "start": "14:00", "end": "15:30", "date": null}

"o que fiz na sexta"
→ {"action": "query", "query_type": "day", "date": "2026-04-08", "keyword": ""}

"resumo da semana"
→ {"action": "summary", "query_type": "week", "date": "2026-04-07"}
"""


def interpret(text: str, llm: LLMClient, lang: str = "pt", now: datetime | None = None) -> ActivityIntent:
    """Parse activity log text and return ActivityIntent. Never raises."""
    if not has_activity_log_signal(text):
        return ActivityIntent(action="none")

    if now is None:
        now = datetime.now()

    # ── Try local parsing first ───────────────────────────────────────────
    intent = _try_local_parse(text, lang, now)
    if intent is not None:
        return intent

    # ── LLM fallback ─────────────────────────────────────────────────────
    try:
        weekday = now.strftime("%A")
        stamped = f"[now: {now.strftime('%Y-%m-%d %H:%M')} {weekday}]\n{text}"
        raw = llm.complete(stamped, system=_SYSTEM_PROMPT)
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(raw)
    except Exception:
        return ActivityIntent(action="none")

    action = data.get("action", "none")
    if action == "log":
        return ActivityIntent(
            action="log",
            title=data.get("title", ""),
            duration_minutes=int(data.get("duration_minutes", 60)),
            target_date=_parse_date_field(data.get("date"), now),
        )
    elif action == "query":
        return ActivityIntent(
            action="query",
            query_type=data.get("query_type", "day"),
            query_date=_parse_date_field(data.get("date"), now),
            query_keyword=data.get("keyword", ""),
        )
    elif action == "summary":
        return ActivityIntent(
            action="summary",
            query_type=data.get("query_type", "week"),
            query_date=_parse_date_field(data.get("date"), now),
        )

    return ActivityIntent(action="none")


def _try_local_parse(text: str, lang: str, now: datetime) -> ActivityIntent | None:
    """Attempt to parse activity log intent locally. Returns None if not possible."""
    lower = text.lower()

    # ── Query patterns ────────────────────────────────────────────────────
    for pat, qtype in _QUERY_PATTERNS.get(lang, []):
        m = pat.search(text)
        if m:
            if qtype == "summary":
                query_date = _parse_date(text, now) or _monday_of_current_week(now)
                return ActivityIntent(action="summary", query_type="week", query_date=query_date)
            elif qtype == "duration":
                # "quanto tempo em reuniões essa semana"
                rest = m.group(2) if m.lastindex else ""
                query_date = _parse_date(text, now)
                return ActivityIntent(
                    action="query", query_type="keyword",
                    query_date=query_date, query_keyword=rest.strip(),
                )
            elif qtype == "keyword":
                rest = m.group(2) if m.lastindex else ""
                return ActivityIntent(action="query", query_type="keyword", query_keyword=rest.strip())
            elif qtype == "keyword_or_date":
                rest = m.group(2) if m.lastindex else ""
                target_date = _parse_date(text, now)
                if target_date:
                    return ActivityIntent(action="query", query_type="day", query_date=target_date)
                return ActivityIntent(action="query", query_type="keyword", query_keyword=rest.strip())

    # ── Log patterns ──────────────────────────────────────────────────────
    # Check for log signals
    has_log = any(v in lower for v in _LOG_VERBS_PT) or any(v in lower for v in _LOG_VERBS_EN)
    has_noun = any(n in lower for n in _LOG_NOUNS)

    if not has_log and not has_noun:
        return None

    intent = ActivityIntent(action="log")
    intent.title = _extract_title(text, lang)

    # Date
    target_date = _parse_date(text, now)
    if target_date:
        intent.target_date = target_date

    # Duration
    duration = _parse_duration(text)
    if duration > 0:
        intent.duration_minutes = duration

    # Time range
    time_range = _parse_time_range(text)
    if time_range:
        sh, sm, eh, em = time_range
        from datetime import datetime as dt
        base_date = intent.target_date or now.date()
        intent.start = dt(base_date.year, base_date.month, base_date.day, sh, sm)
        intent.end = dt(base_date.year, base_date.month, base_date.day, eh, em)
        intent.duration_minutes = (eh * 60 + em) - (sh * 60 + sm)
        if intent.duration_minutes <= 0:
            intent.duration_minutes += 24 * 60  # Cross midnight

    if intent.duration_minutes == 0:
        intent.duration_minutes = 60  # Default

    return intent


def _parse_date_field(value: str | None, now: datetime):
    """Parse a YYYY-MM-DD string or return None."""
    if not value:
        return None
    try:
        from datetime import date
        parts = value.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None


def _monday_of_current_week(now: datetime):
    """Return the Monday of the current week."""
    from datetime import timedelta
    return now.date() - timedelta(days=now.weekday())
