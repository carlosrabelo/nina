"""Interpret free-text messages and extract a presence action using the LLM."""

import json
import re
from dataclasses import dataclass

from nina.core.llm.client import LLMClient
from nina.skills.presence.models import PresenceStatus

_KEYWORDS: dict[str, set[str]] = {
    "pt": {"home", "casa", "escritório", "escritorio", "saindo", "saí", "sai",
           "cheguei", "chegando", "chegar", "chego", "dnd", "foco", "presença",
           "trabalhando", "trabalho", "voltei", "no escritório", "em casa",
           "no trabalho", "home office"},
    "en": {"home", "office", "out", "dnd", "focus", "arrived", "arriving",
           "leaving", "presence", "working", "work", "at work", "at home"},
}


def has_context(text: str, lang: str = "pt") -> bool:
    """Keyword gate — no LLM."""
    lower = text.lower()
    return any(kw in lower for kw in _KEYWORDS.get(lang, _KEYWORDS["pt"]))


_SYSTEM_PROMPT = """You are an assistant that interprets presence status from natural language messages.

The available presence statuses are:
- home: working from home, just arrived home, at home
- office: at the office, arrived at work or office building
- out: going out, on the move, traveling, running errands, outside, lunch break
- dnd: do not disturb — in a meeting, training session, course, lecture, presentation,
       workshop, focused work, studying, on a call, busy and unavailable

Analyze the user's message and return a JSON object with:
- "action": "set_presence" if the message clearly indicates a presence change, otherwise "none"
- "status": one of "home", "office", "out", "dnd" (only when action is "set_presence")
- "note": a brief note extracted from the message, in the same language as the input (can be empty string)

Return ONLY valid JSON, no explanation, no markdown.

Examples:
"Acabei de chegar no trabalho" -> {"action": "set_presence", "status": "office", "note": ""}
"Saindo para almoço" -> {"action": "set_presence", "status": "out", "note": "almoço"}
"Não me perturbe, estou em reunião" -> {"action": "set_presence", "status": "dnd", "note": "em reunião"}
"Estou num treinamento" -> {"action": "set_presence", "status": "dnd", "note": "treinamento"}
"Estou num curso agora" -> {"action": "set_presence", "status": "dnd", "note": "curso"}
"Em uma apresentação" -> {"action": "set_presence", "status": "dnd", "note": "apresentação"}
"Preciso focar, não me interrompa" -> {"action": "set_presence", "status": "dnd", "note": "foco"}
"Cheguei em casa" -> {"action": "set_presence", "status": "home", "note": ""}
"Vou trabalhar de casa hoje" -> {"action": "set_presence", "status": "home", "note": "home office"}
"Just got to the office" -> {"action": "set_presence", "status": "office", "note": ""}
"In a training session" -> {"action": "set_presence", "status": "dnd", "note": "training"}
"Qual é o tempo hoje?" -> {"action": "none"}
"""


@dataclass
class PresenceIntent:
    action: str          # "set_presence" | "none"
    status: PresenceStatus | None = None
    note: str = ""


def interpret(text: str, llm: LLMClient) -> PresenceIntent:
    """Parse *text* and return a PresenceIntent. Never raises — returns action=none on any error."""
    try:
        raw = llm.complete(text, system=_SYSTEM_PROMPT)
        # Strip markdown code fences if the LLM wraps output
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(raw)
    except Exception:
        return PresenceIntent(action="none")

    if data.get("action") != "set_presence":
        return PresenceIntent(action="none")

    try:
        status = PresenceStatus(data["status"])
    except (KeyError, ValueError):
        return PresenceIntent(action="none")

    return PresenceIntent(
        action="set_presence",
        status=status,
        note=str(data.get("note", "")),
    )
