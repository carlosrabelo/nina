"""Local intent router — pattern/regex matching before LLM fallback.

This is Layer 2 in the intent routing pipeline:
  Layer 1: keyword gate (per-skill try_action) — zero LLM
  Layer 2: local_router — advanced regex patterns, entity extraction — zero LLM
  Layer 3: LLM-based RouterIntent — fallback when patterns fail
  Layer 4: Dedicated interpreters (blocking, workdays) — second LLM call

All functions return None when they cannot match, allowing fallback to the next layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nina.core.nlp import (
    parse_date_relative,
    parse_duration,
    parse_time,
)
from nina.skills.activity_log.patterns import has_activity_log_signal

# ── Presence patterns ────────────────────────────────────────────────────────

# ── Presence: keyword scoring ────────────────────────────────────────────────
# Each keyword has a weight. The status with highest total score wins.
# Multi-word phrases score higher than individual words, avoiding ambiguity.

_SCORES: dict[str, dict[str, int]] = {
    "home": {
        "casa": 3,
        "em casa": 4,
        "cheguei em casa": 5,
        "cheguei casa": 5,
        "home office": 4,
        "trabalho de casa": 4,
        "trabalhando de casa": 4,
        "voltei": 1,
        "disponível": 2,
        "livre": 1,
    },
    "work": {
        "trabalho": 3,
        "cheguei": 1,
        "chegando": 1,
        "chegar": 1,
        "escritório": 3,
        "escritorio": 3,
        "no escritório": 4,
        "no escritorio": 4,
        "no trabalho": 4,
        "campus": 3,
        "no campus": 4,
        "presencial": 2,
    },
    "out": {
        "saindo": 3,
        "saí": 4,
        "sai": 4,
        "almoço": 3,
        "almoco": 3,
        "saindo para o almoço": 5,
        "rua": 2,
        "cliente": 2,
        "externo": 2,
        "pausa": 1,
        "intervalo": 1,
    },
    "dnd": {
        "reunião": 3,
        "reuniao": 3,
        "em reunião": 4,
        "em reuniao": 4,
        "treinamento": 3,
        "treino": 2,
        "curso": 2,
        "apresentação": 3,
        "apresentacao": 3,
        "palestra": 2,
        "workshop": 2,
        "foco": 2,
        "ocupado": 2,
        "ocupad": 2,
    },
}

_SCORE_THRESHOLD = 2  # minimum score to consider a match

# Keywords that indicate workdays (schedule change), not current presence
_WORKDAYS_KEYWORDS = {
    "segunda", "terça", "terca", "quarta", "quinta", "sexta",
    "sábado", "sabado", "domingo",
    "horário", "horario", "fuso", "timezone",
    "não trabalho", "saio às", "saio as",
}


def _is_workdays_context(text: str) -> bool:
    """Check if text is about changing work schedule, not current status."""
    lower = text.lower()
    # "trabalho de segunda a sexta" → workdays
    if "de " in lower and " a " in lower and any(
        d in lower for d in ["segunda", "terça", "terca", "quarta", "quinta", "sexta"]
    ):
        return True
    return any(kw in lower for kw in _WORKDAYS_KEYWORDS)


def _score_presence(text: str, lang: str = "pt") -> tuple[str, int]:
    """Score each presence status by keyword matches. Returns (status, score)."""
    if _is_workdays_context(text):
        return "", 0
    if lang != "pt":
        # English fallback: simple keyword match
        en_scores = {
            "home": {"at home": 4, "home": 3, "home office": 4, "working from home": 5,
                     "back": 1, "available": 2, "free now": 2},
            "work": {"at the office": 4, "at work": 4, "office": 3, "campus": 3,
                     "arrived": 1, "on site": 3, "just got": 3, "at the campus": 5},
            "out": {"going out": 4, "lunch": 3, "on the move": 3, "errands": 2},
            "dnd": {"meeting": 3, "in a meeting": 5, "training": 3, "workshop": 2,
                    "presentation": 3, "course": 2, "deep focus": 3, "busy": 2},
        }
        return _score_with(en_scores, text)
    return _score_with(_SCORES, text)


def _score_with(scores: dict[str, dict[str, int]], text: str) -> tuple[str, int]:
    """Generic scoring: sum weights for each status, return the winner."""
    lower = text.lower()
    totals: dict[str, int] = {}
    for status, words in scores.items():
        score = 0
        # Sort by length descending so multi-word phrases are checked first
        for phrase in sorted(words, key=len, reverse=True):
            if phrase in lower:
                score += words[phrase]
                # Remove matched phrase to avoid double-counting
                lower = lower.replace(phrase, "", 1)
        totals[status] = score

    # Find the winner
    best_status = max(totals, key=totals.get)  # type: ignore[arg-type]
    best_score = totals[best_status]
    if best_score >= _SCORE_THRESHOLD:
        return best_status, best_score
    return "", 0


@dataclass
class LocalIntent:
    """Result from local pattern matching."""

    domain: str  # presence, memo, calendar, notifications, blocking, none
    action: str = "none"
    entities: dict[str, Any] = field(default_factory=dict)  # extracted entities


def try_presence(text: str, lang: str = "pt") -> LocalIntent | None:
    """Match presence by keyword scoring. Returns LocalIntent or None."""
    status, score = _score_presence(text, lang)
    if status:
        return LocalIntent(
            domain="presence",
            action="set_presence",
            entities={"status": status, "note": ""},
        )
    return None


# ── Memo patterns ────────────────────────────────────────────────────────────

# "me lembra de {ação} {data}", "me avisa {data} para {ação}"
_REMINDER_PATTERNS: dict[str, list[re.Pattern]] = {
    "pt": [
        re.compile(
            r"(?:me\s+lembra|me\s+lembre|me\s+avisa|me\s+avise|lembrete)[\s:]+(.+)",
            re.I,
        ),
    ],
    "en": [
        re.compile(r"(?:remind\s+me|remember|don['']t\s+forget)[\s:]+(.+)", re.I),
    ],
}

# "memo {texto}", "cria memo {texto}", "adiciona memo {texto}"
_MEMO_CREATE_PATTERNS: dict[str, list[re.Pattern]] = {
    "pt": [
        re.compile(r"(?:cri[ea]|adiciona|novo|nova|salva|salve)\s+memo\s+(.+)", re.I),
        re.compile(r"memo\s+(?!done|dismiss|list)(.+)", re.I),
    ],
    "en": [
        re.compile(r"(?:create|add|new|save)\s+memo\s+(.+)", re.I),
        re.compile(r"memo\s+(?!done|dismiss|list)(.+)", re.I),
    ],
}

_MEMO_LIST_PATTERNS: dict[str, list[re.Pattern]] = {
    "pt": [
        re.compile(
            r"(?:quais\s+(meus?\s+)?memos|lista[r]?\s+memos|memos\s+abertos)", re.I
        )
    ],
    "en": [re.compile(r"(?:my?\s+memos|list\s+memos|open\s+memos)", re.I)],
}


def try_memo(
    text: str, lang: str = "pt", now: datetime | None = None
) -> LocalIntent | None:
    """Match memo patterns. Returns LocalIntent or None."""
    # Memo list
    for pat in _MEMO_LIST_PATTERNS.get(lang, _MEMO_LIST_PATTERNS["pt"]):
        if pat.search(text):
            return LocalIntent(domain="memo", action="list")

    # Reminder with date: "me lembra de ligar amanhã às 10h"
    for pat in _REMINDER_PATTERNS.get(lang, _REMINDER_PATTERNS["pt"]):
        m = pat.search(text)
        if m:
            subject = m.group(1).strip()
            entities: dict[str, Any] = {"subject": subject}
            # Try to extract date/time
            time_ent = parse_time(subject)
            date_ent = parse_date_relative(subject, now) if now else None
            if time_ent and date_ent:
                h = f"{time_ent.hour:02d}:{time_ent.minute:02d}"
                entities["due_date"] = f"{date_ent.date.isoformat()} {h}"
            elif date_ent:
                # Default to 9:00 if only date
                entities["due_date"] = f"{date_ent.date.isoformat()} 09:00"
            elif time_ent and now:
                # Same day at given time
                h = f"{time_ent.hour:02d}:{time_ent.minute:02d}"
                entities["due_date"] = f"{now.date().isoformat()} {h}"
            return LocalIntent(domain="memo", action="remind", entities=entities)

    # Memo create: "memo comprar pão"
    for pat in _MEMO_CREATE_PATTERNS.get(lang, _MEMO_CREATE_PATTERNS["pt"]):
        m = pat.search(text)
        if m:
            return LocalIntent(
                domain="memo",
                action="create",
                entities={"subject": m.group(1).strip()},
            )

    return None


# ── Calendar patterns ────────────────────────────────────────────────────────

_CALENDAR_PATTERNS: dict[str, list[tuple[re.Pattern, str]]] = {
    "pt": [
        (
            re.compile(
                r"\b(meus?\s+(eventos|compromissos)|o\s+que\s+tenho\s+(hoje|amanh[ãa])|minha\s+agenda|pr[óo]ximos?\s+eventos)",
                re.I,
            ),
            "list",
        ),
        (
            re.compile(
                r"\b(eventos?\s+(de\s+)?(hoje|amanh[ãa])|agenda\s+(de\s+)?(hoje|amanh[ãa]))",
                re.I,
            ),
            "list",
        ),
    ],
    "en": [
        (
            re.compile(
                r"\b(my?\s+events?|what[']?s?\s+on\s+(today|tomorrow)|my?\s+schedule|upcoming\s+events?)",
                re.I,
            ),
            "list",
        ),
        (
            re.compile(
                r"\b(events?\s+(today|tomorrow)|schedule\s+(today|tomorrow))", re.I
            ),
            "list",
        ),
    ],
}


def try_calendar(text: str, lang: str = "pt") -> LocalIntent | None:
    """Match calendar patterns. Returns LocalIntent or None."""
    patterns = _CALENDAR_PATTERNS.get(lang, _CALENDAR_PATTERNS["pt"])
    for pat, action in patterns:
        if pat.search(text):
            return LocalIntent(domain="calendar", action=action)
    return None


# ── Notification patterns ────────────────────────────────────────────────────

_NOTIF_REMINDER_RE = re.compile(r"\b(\d+)\s*(?:minuto[s]?|minute[s]?|min)\b", re.I)
_NOTIF_DAYS_RE = re.compile(r"\b(\d+)\s*(?:dia[s]?|day[s]?)\b", re.I)

_NOTIF_GET_PATTERNS: dict[str, list[re.Pattern]] = {
    "pt": [
        re.compile(
            r"(?:quais\s+(minhas?\s+)?notific|ver\s+notific|minhas?\s+notific)", re.I
        )
    ],
    "en": [re.compile(r"(?:my?\s+notifications?|show\s+notif)", re.I)],
}

_NOTIF_REMINDER_PATTERNS: dict[str, list[re.Pattern]] = {
    "pt": [
        re.compile(
            r"(?:avisa|notifica|lembra|lembrete|notific)[^\d]*(\d+)\s*(?:minuto[s]?|min)",
            re.I,
        ),
        re.compile(
            r"(\d+)\s*(?:minuto[s]?|min)[^\d]*(?:antes|anteced[êe]ncia|aviso)", re.I
        ),
    ],
    "en": [
        re.compile(r"(?:notify|reminder|remind)[^\d]*(\d+)\s*(?:minute[s]?|min)", re.I),
        re.compile(r"(\d+)\s*(?:minute[s]?|min)[^\d]*(?:before|advance)", re.I),
    ],
}

_NOTIF_DAYS_PATTERNS: dict[str, list[re.Pattern]] = {
    "pt": [
        re.compile(r"(\d+)\s*(?:dia[s]?)[^\d]*(?:anteced[êe]ncia|antes|monitor)", re.I),
        re.compile(r"(?:notific|aviso|lembrete)[^\d]*(\d+)\s*(?:dia[s]?)", re.I),
    ],
    "en": [
        re.compile(r"(\d+)\s*(?:day[s]?)[^\d]*(?:before|ahead|watch)", re.I),
        re.compile(r"(?:notif|reminder)[^\d]*(\d+)\s*(?:day[s]?)", re.I),
    ],
}


def try_notifications(text: str, lang: str = "pt") -> LocalIntent | None:
    """Match notification patterns. Returns LocalIntent or None."""
    # Get settings
    for pat in _NOTIF_GET_PATTERNS.get(lang, _NOTIF_GET_PATTERNS["pt"]):
        if pat.search(text):
            return LocalIntent(domain="notifications", action="get")

    # Set reminder minutes
    for pat in _NOTIF_REMINDER_PATTERNS.get(lang, _NOTIF_REMINDER_PATTERNS["pt"]):
        m = pat.search(text)
        if m:
            return LocalIntent(
                domain="notifications",
                action="set_reminder",
                entities={"minutes": int(m.group(1))},
            )

    # Set watch days
    for pat in _NOTIF_DAYS_PATTERNS.get(lang, _NOTIF_DAYS_PATTERNS["pt"]):
        m = pat.search(text)
        if m:
            return LocalIntent(
                domain="notifications",
                action="set_days",
                entities={"days": int(m.group(1))},
            )

    # Fallback: just a number with notification keyword
    notif_keywords_pt = {"notific", "lembrete", "avisa", "alerta"}
    notif_keywords_en = {"notif", "reminder", "alert"}
    kw_set = notif_keywords_pt if lang == "pt" else notif_keywords_en
    lower = text.lower()
    if any(kw in lower for kw in kw_set):
        m = _NOTIF_REMINDER_RE.search(text)
        if m:
            return LocalIntent(
                domain="notifications",
                action="set_reminder",
                entities={"minutes": int(m.group(1))},
            )
        m = _NOTIF_DAYS_RE.search(text)
        if m:
            return LocalIntent(
                domain="notifications",
                action="set_days",
                entities={"days": int(m.group(1))},
            )

    return None


# ── Blocking patterns ────────────────────────────────────────────────────────

_BLOCKING_ACTION_PATTERNS: dict[str, list[re.Pattern]] = {
    "pt": [
        re.compile(r"(?:agenda|r?cria|r?bloqueia|marca)\s+(.+)", re.I),
        re.compile(r"(.+?)\s+(?:por\s+\d+\s*(?:h|min)|[àa]s\s+\d)", re.I),
    ],
    "en": [
        re.compile(r"(?:schedule|book|block)\s+(.+)", re.I),
        re.compile(r"(.+?)\s+(?:for\s+\d+\s*(?:h|hour|min)|at\s+\d)", re.I),
    ],
}


def try_blocking(text: str, lang: str = "pt") -> LocalIntent | None:
    """Match blocking (calendar scheduling) patterns.

    Requires both a time reference (hour or duration) AND an action keyword.
    Returns LocalIntent or None.
    """
    has_time = parse_time(text) is not None
    has_duration = parse_duration(text) is not None
    if not has_time and not has_duration:
        return None

    patterns = _BLOCKING_ACTION_PATTERNS.get(lang, _BLOCKING_ACTION_PATTERNS["pt"])
    for pat in patterns:
        m = pat.search(text)
        if m:
            title = m.group(1).strip() if m.lastindex else text
            entities: dict[str, Any] = {"title": title}
            if has_time:
                entities["time"] = parse_time(text)
            if has_duration:
                entities["duration"] = parse_duration(text)
            return LocalIntent(domain="blocking", action="create", entities=entities)

    return None


# ── Activity log patterns ────────────────────────────────────────────────────


def try_activity_log(
    text: str, lang: str = "pt", now: datetime | None = None
) -> LocalIntent | None:
    """Match activity logging patterns. Returns LocalIntent or None."""
    if not has_activity_log_signal(text):
        return None

    # Delegate to the activity_log interpreter's local parsing
    from nina.skills.activity_log.interpreter import _try_local_parse

    if now is None:
        now = datetime.now()

    intent = _try_local_parse(text, lang, now)
    if intent is None:
        return None

    entities: dict[str, Any] = {
        "title": intent.title,
        "duration_minutes": intent.duration_minutes,
    }
    if intent.start:
        entities["start"] = intent.start.isoformat()
    if intent.end:
        entities["end"] = intent.end.isoformat()
    if intent.target_date:
        entities["date"] = intent.target_date.isoformat()
    if intent.query_type:
        entities["query_type"] = intent.query_type
    if intent.query_keyword:
        entities["query_keyword"] = intent.query_keyword
    if intent.query_date:
        entities["query_date"] = intent.query_date.isoformat()

    return LocalIntent(
        domain="activity_log",
        action=intent.action,
        entities=entities,
    )


# ── Orchestrator ─────────────────────────────────────────────────────────────


def route(
    text: str, lang: str = "pt", now: datetime | None = None
) -> LocalIntent | None:
    """Try all local patterns in priority order. Returns first match or None.

    Priority: presence > activity_log > memo > calendar > notifications > blocking
    """
    for fn in [
        lambda: try_presence(text, lang),
        lambda: try_activity_log(text, lang, now),
        lambda: try_memo(text, lang, now),
        lambda: try_calendar(text, lang),
        lambda: try_notifications(text, lang),
        lambda: try_blocking(text, lang),
    ]:
        result = fn()
        if result is not None:
            return result
    return None
