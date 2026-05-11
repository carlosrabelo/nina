# nina/skills/calendar/interpreter.py
"""Calendar intent interpreter — local_router first, LLM fallback."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

_KEYWORDS: dict[str, set[str]] = {
    "pt": {"evento", "eventos", "calendário", "agenda", "compromisso", "compromissos"},
    "en": {"event", "events", "calendar", "agenda", "meeting", "meetings"},
}

_SYSTEM_PROMPT = """\
You are a command parser for the calendar domain in a personal assistant.
The user message may be in Portuguese or English.
Return JSON only — no explanation, no markdown.
Schema: {
  "action": "list|search|free_busy|none",
  "calendar_window": "upcoming|today|tomorrow|week|days",
  "calendar_span_days": <int or null>,
  "calendar_keyword": "<string or null>",
  "calendar_period": "full|morning|afternoon"
}
Actions:
  list — show calendar events in a window (default upcoming)
  search — filter events by calendar_keyword in title/location
  free_busy — when the user asks if they are free / available in a window
  none — not a calendar action
If unsure, return {"action": "none"}.
"""


@dataclass
class CalendarIntent:
    action: str  # list | search | free_busy | none
    window: str = "upcoming"
    span_days: int | None = None
    keyword: str = ""
    period: str = "full"


def try_action(
    text: str, lang: str = "pt", now: datetime | None = None
) -> CalendarIntent | None:
    """Layer 1 — delegate to local_router calendar patterns. None if no match."""
    from nina.core.intent.local_router import try_calendar

    li = try_calendar(text, lang, now)
    if li is None:
        return None
    e = li.entities
    return CalendarIntent(
        action=li.action,
        window=str(e.get("calendar_window") or "upcoming"),
        span_days=e.get("calendar_span_days")
        if isinstance(e.get("calendar_span_days"), int)
        else None,
        keyword=str(e.get("calendar_keyword") or ""),
        period=str(e.get("calendar_period") or "full"),
    )


def interpret(text: str, llm, lang: str = "pt") -> CalendarIntent:
    """Layer 2 — LLM fallback. Returns CalendarIntent (action may be 'none')."""
    keywords = _KEYWORDS.get(lang, _KEYWORDS["pt"])
    if not any(kw in text.lower() for kw in keywords):
        return CalendarIntent(action="none")
    try:
        raw = llm.complete(text, system=_SYSTEM_PROMPT)
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(raw)
    except Exception:
        return CalendarIntent(action="none")

    act = str(data.get("action", "none"))
    if act not in ("list", "search", "free_busy", "none"):
        act = "none"
    return CalendarIntent(
        action=act,
        window=str(data.get("calendar_window") or "upcoming"),
        span_days=_coerce_int(data.get("calendar_span_days")),
        keyword=str(data.get("calendar_keyword") or ""),
        period=str(data.get("calendar_period") or "full"),
    )


def _coerce_int(v: Any) -> int | None:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        return int(v.strip())
    return None
