# nina/google/calendar/interpreter.py
"""Calendar intent interpreter — hybrid pattern match + LLM fallback."""

import json
from dataclasses import dataclass

_KEYWORDS: dict[str, set[str]] = {
    "pt": {"evento", "eventos", "calendário", "agenda"},
    "en": {"event", "events", "calendar", "agenda"},
}

def has_context(text: str, lang: str = "pt") -> bool:
    """Keyword gate — no LLM."""
    lower = text.lower()
    return any(kw in lower for kw in _KEYWORDS.get(lang, _KEYWORDS["pt"]))


_ACTION_WORDS: dict[str, dict[str, set[str]]] = {
    "pt": {
        "list": {"quais", "liste", "listar", "mostre", "mostrar", "ver", "veja",
                 "exibir", "exiba", "próximos", "proximos"},
    },
    "en": {
        "list": {"list", "show", "display", "upcoming"},
    },
}

_SYSTEM_PROMPT = """\
You are a command parser for the calendar domain in a personal assistant.
The user message may be in Portuguese or English.
Return JSON only — no explanation, no markdown.
Schema: {"action": "list|none"}
Actions:
  list — show upcoming calendar events
  none — not a calendar action
If unsure, return {"action": "none"}.
"""


@dataclass
class CalendarIntent:
    action: str   # "list" | "none"


def try_action(text: str, lang: str = "pt") -> CalendarIntent | None:
    """Layer 1 — pattern match. Returns CalendarIntent or None (no LLM)."""
    lower = text.lower()
    keywords = _KEYWORDS.get(lang, _KEYWORDS["pt"])
    if not any(kw in lower for kw in keywords):
        return None

    words_by_action = _ACTION_WORDS.get(lang, _ACTION_WORDS["pt"])
    for action, words in words_by_action.items():
        if any(w in lower for w in words):
            return CalendarIntent(action=action)

    return None


def interpret(text: str, llm, lang: str = "pt") -> CalendarIntent:
    """Layer 2 — LLM fallback. Returns CalendarIntent (action may be 'none')."""
    keywords = _KEYWORDS.get(lang, _KEYWORDS["pt"])
    if not any(kw in text.lower() for kw in keywords):
        return CalendarIntent(action="none")
    try:
        raw = llm.complete(text, system=_SYSTEM_PROMPT)
        data = json.loads(raw)
        return CalendarIntent(action=data.get("action", "none"))
    except Exception:
        return CalendarIntent(action="none")
