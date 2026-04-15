"""Patterns for parsing activity logging commands (local, no LLM).

Supported input formats (PT):
    "fiz deploy da feature X"          → log, today, no time
    "fiz deploy da feature X ontem"    → log, yesterday
    "estive em reunião com time por 1h" → log, duration=60
    "estive em reunião com time por 1h30" → log, duration=90
    "reunião com cliente das 14h às 15h30" → log, start/end
    "almoço com cliente ontem das 12h às 13h" → log, date=yesterday
    "o que fiz na sexta"               → query, date=friday
    "o que fiz ontem"                  → query, date=yesterday
    "resumo da semana"                 → summary, week=current
    "resumo da semana passada"         → summary, week=previous
    "quais reuniões tive com o cliente X" → query, keyword
    "quanto tempo em reuniões essa semana" → query, keyword/duration
"""
# ruff: noqa: E501 — docstring examples exceed 88 chars

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

# ── Date resolution ──────────────────────────────────────────────────────────

_DATE_WORDS_PT: dict[str, int] = {
    "hoje": 0, "ontem": -1, "anteontem": -2,
}
_DATE_WORDS_EN: dict[str, int] = {
    "today": 0, "yesterday": -1,
}

_WEEKDAYS_PT = [
    "segunda", "terça", "terca", "quarta",
    "quinta", "sexta", "sábado", "sabado", "domingo",
]
_WEEKDAYS_EN = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]

# ── Duration patterns ────────────────────────────────────────────────────────

_DURATION_RE = re.compile(r"(\d+)h(\d+)(?:min)?", re.I)
_DURATION_HOUR_RE = re.compile(r"(?:por\s+)?(\d+)\s*h(?:ora[s]?)?", re.I)
_DURATION_MIN_RE = re.compile(r"(?:por\s+)?(\d+)\s*min(?:uto[s]?)?", re.I)
_DURATION_TEXT_PT = re.compile(
    r"(?:por\s+)?(uma\s+hora|meia\s+hora|"
    r"duas?\s+horas?|três\s+horas?)",
    re.I,
)

_DURATION_MAP = {
    "uma hora": 60, "meia hora": 30, "duas horas": 120,
    "duas hora": 120, "três horas": 180, "tres horas": 180,
}

# ── Time range patterns ─────────────────────────────────────────────────────

# "das 14h às 15h30", "from 2pm to 3:30pm", "de 9h a 10h"
_TIME_RANGE_PT = re.compile(
    r"(?:das|de|from)\s+(\d{1,2})[h:](\d{2})?\s+(?:[àa]s?|to|até)\s+(\d{1,2})[h:](\d{2})?",
    re.I,
)
_TIME_RANGE_EN = re.compile(
    r"(?:from|at)\s+(\d{1,2})[:](\d{2})?\s+(?:to|until)\s+(\d{1,2})[:](\d{2})?",
    re.I,
)

# ── Action keywords ──────────────────────────────────────────────────────────

_LOG_VERBS_PT = {"fiz", "criei", "montei", "implementei", "terminei", "completei",
                 "estive", "participei", "tive", "fui", "atendi", "review",
                 "deploy", "debug", "debuguei", "resolvi", "corrigei"}
_LOG_VERBS_EN = {"did", "created", "built", "implemented", "finished", "completed",
                 "was in", "attended", "went to", "deployed", "debugged", "resolved",
                 "fixed"}

_LOG_NOUNS = {"reunião", "reuniao", "call", "meeting", "deploy", "review",
              "debug", "teste", "test", "aula", "class", "curso", "course",
              "treinamento", "training", "workshop", "apresentação", "presentation",
              "almoço", "almoco", "lunch", "janta", "dinner"}

# ── Query keywords ───────────────────────────────────────────────────────────

_QUERY_PATTERNS: dict[str, list[tuple[re.Pattern, str]]] = {
    "pt": [
        (re.compile(r"o\s+que\s+(eu\s+)?fiz\s+(.+)", re.I), "keyword_or_date"),
        (re.compile(r"quais?\s+(reuni[õo]es?|calls?|meetings?)\s+(.+)", re.I), "keyword"),
        (re.compile(r"resumo\s+(da\s+semana|do\s+dia|de\s+(.+))", re.I), "summary"),
        (re.compile(r"quanto\s+tempo\s+(em|nas?)\s+(.+)", re.I), "duration"),
    ],
    "en": [
        (re.compile(r"what\s+(did|i)\s+(do|did)\s+(.+)", re.I), "keyword_or_date"),
        (re.compile(r"which?\s+(meetings?|calls?)\s+(.+)", re.I), "keyword"),
        (re.compile(r"(weekly|daily)\s+summary", re.I), "summary"),
        (re.compile(r"how\s+much\s+time\s+(in|on)\s+(.+)", re.I), "duration"),
    ],
}


def _parse_duration(text: str) -> int:
    """Extract duration in minutes from text. Returns 0 if not found."""
    # "1h30"
    m = _DURATION_RE.search(text)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    # "2 horas"
    m = _DURATION_HOUR_RE.search(text)
    if m:
        return int(m.group(1)) * 60
    # "30 minutos"
    m = _DURATION_MIN_RE.search(text)
    if m:
        return int(m.group(1))
    # "uma hora", "meia hora"
    m = _DURATION_TEXT_PT.search(text)
    if m:
        return _DURATION_MAP.get(m.group(1).lower(), 0)
    return 0


def _parse_time_range(text: str) -> tuple[int, int, int, int] | None:
    """Extract start/end times as (sh, sm, eh, em). Returns None if not found."""
    m = _TIME_RANGE_PT.search(text)
    if not m:
        m = _TIME_RANGE_EN.search(text)
    if not m:
        return None
    sh = int(m.group(1))
    sm = int(m.group(2)) if m.group(2) else 0
    eh = int(m.group(3))
    em = int(m.group(4)) if m.group(4) else 0
    if 0 <= sh <= 23 and 0 <= sm <= 59 and 0 <= eh <= 23 and 0 <= em <= 59:
        return sh, sm, eh, em
    return None


def _parse_date(text: str, now: datetime) -> date | None:
    """Resolve date from text. Returns None if no date found."""
    lower = text.lower()

    # "hoje", "ontem"
    for word, offset in _DATE_WORDS_PT.items():
        if word in lower:
            return now.date() + timedelta(days=offset)
    for word, offset in _DATE_WORDS_EN.items():
        if word in lower:
            return now.date() + timedelta(days=offset)

    # "na segunda", "on monday"
    for i, day_pt in enumerate(_WEEKDAYS_PT):
        if day_pt in lower:
            return _next_or_prev_weekday(i, now)
    for i, day_en in enumerate(_WEEKDAYS_EN):
        if day_en in lower:
            return _next_or_prev_weekday(i, now)

    # "essa semana", "this week"
    if "essa semana" in lower or "this week" in lower:
        return _monday_of_current_week(now)
    if "semana passada" in lower or "last week" in lower:
        return _monday_of_current_week(now) - timedelta(days=7)

    return None


def _next_or_prev_weekday(target_idx: int, now: datetime) -> date:
    """Return the most recent occurrence of the target weekday."""
    today_idx = now.weekday()
    days_back = today_idx - target_idx
    if days_back <= 0:
        days_back += 7  # Go to previous week
    return now.date() - timedelta(days=days_back)


def _monday_of_current_week(now: datetime) -> date:
    """Return the Monday of the current week."""
    return now.date() - timedelta(days=now.weekday())


def has_activity_log_signal(text: str) -> bool:
    """Check if text has activity logging signals (Layer 1 gate)."""
    lower = text.lower()
    # Check for log verbs
    if any(v in lower for v in _LOG_VERBS_PT) or any(v in lower for v in _LOG_VERBS_EN):
        return True
    # Check for log nouns
    if any(n in lower for n in _LOG_NOUNS):
        return True
    # Check for query patterns
    for lang in ["pt", "en"]:
        for pat, _ in _QUERY_PATTERNS.get(lang, []):
            if pat.search(text):
                return True
    # Check for duration + noun combo ("reunião por 1h")
    if _parse_duration(text) > 0 and any(n in lower for n in _LOG_NOUNS):
        return True
    return False
