# nina/intent/router.py
"""Single-call LLM router — classifies text into a domain before dispatching."""

import json
from dataclasses import dataclass

_VALID_DOMAINS = {
    "memo", "calendar", "blocking", "presence", "schedule",
    "profile", "obsidian", "notifications", "none",
}

_SYSTEM_PROMPT = """\
You are a domain router for a personal assistant.
Classify the user message into the most appropriate domain.
Return JSON only — no explanation, no markdown.
Schema: {"domain": "<domain>"}

Domains:
  memo          — notes/memos: create, list, close, dismiss
  calendar      — listing upcoming calendar events
  blocking      — blocking/scheduling time in the calendar (requires explicit time mention)
  presence      — changing presence status (home, office, out, dnd)
  schedule      — changing work hours or timezone
  profile       — linking email/calendar accounts to presence statuses
  obsidian      — syncing or updating the Obsidian vault
  notifications — changing reminder minutes or watch days for event notifications
  none          — unrecognized or out of scope
"""


@dataclass
class RouterIntent:
    domain: str  # one of _VALID_DOMAINS


def route(text: str, llm) -> RouterIntent:
    """Single LLM call — returns the domain this text belongs to."""
    try:
        raw = llm.complete(text, system=_SYSTEM_PROMPT)
        data = json.loads(raw)
        domain = data.get("domain", "none")
        return RouterIntent(domain=domain if domain in _VALID_DOMAINS else "none")
    except Exception:
        return RouterIntent(domain="none")
