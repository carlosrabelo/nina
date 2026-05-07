# nina/notifications/interpreter.py
"""Notification config intent interpreter — hybrid pattern match + LLM fallback."""

import json
import re
from dataclasses import dataclass

_KEYWORDS: dict[str, set[str]] = {
    "pt": {"notificação", "notificacao", "notificações", "notificacoes",
           "lembrete", "lembretes", "aviso", "avisa", "alerta", "notifica"},
    "en": {"notification", "notifications", "reminder", "reminders",
           "alert", "notify"},
}

# Pattern: "<number> minuto(s)" or "<number> dia(s)" near notification keyword
_REMINDER_PATTERN = re.compile(
    r'\b(\d+)\s*(?:minuto[s]?|minute[s]?|min)\b', re.IGNORECASE
)
_DAYS_PATTERN = re.compile(
    r'\b(\d+)\s*(?:dia[s]?|day[s]?)\b', re.IGNORECASE
)

_SYSTEM_PROMPT = """\
You are a command parser for notification settings in a personal assistant.
The user message may be in Portuguese or English.
Return JSON only — no explanation, no markdown.
Schema: {"action": "set_reminder|set_days|get|none", "minutes": <int|null>, "days": <int|null>}
Actions:
  set_reminder — change how many minutes before an event to send a reminder
  set_days     — change how many days ahead to watch for events
  get          — show current notification settings
  none         — not a notification action
If unsure, return {"action": "none"}.
"""


@dataclass
class NotificationIntent:
    action: str           # "set_reminder" | "set_days" | "get" | "none"
    minutes: int | None = None
    days: int | None = None


def has_context(text: str, lang: str = "pt") -> bool:
    """Keyword gate — no LLM."""
    lower = text.lower()
    return any(kw in lower for kw in _KEYWORDS.get(lang, _KEYWORDS["pt"]))


def try_action(text: str, lang: str = "pt") -> NotificationIntent | None:
    """Layer 1 — pattern match. Returns NotificationIntent or None."""
    if not has_context(text, lang):
        return None

    lower = text.lower()

    # "get" / "show" patterns
    get_words = {"quais", "ver", "mostrar", "show", "listar", "list", "atual", "current"}
    if any(w in lower for w in get_words):
        return NotificationIntent(action="get")

    # set_reminder: number + minutos near notification keyword
    m = _REMINDER_PATTERN.search(text)
    if m:
        return NotificationIntent(action="set_reminder", minutes=int(m.group(1)))

    # set_days: number + dias near notification keyword
    d = _DAYS_PATTERN.search(text)
    if d:
        return NotificationIntent(action="set_days", days=int(d.group(1)))

    return None


def interpret(text: str, llm, lang: str = "pt") -> NotificationIntent:
    """Layer 2 — LLM fallback. Returns NotificationIntent (action may be 'none')."""
    if not has_context(text, lang):
        return NotificationIntent(action="none")
    try:
        raw = llm.complete(text, system=_SYSTEM_PROMPT)
        data = json.loads(raw)
        return NotificationIntent(
            action=data.get("action", "none"),
            minutes=data.get("minutes"),
            days=data.get("days"),
        )
    except Exception:
        return NotificationIntent(action="none")
