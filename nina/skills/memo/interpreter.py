# nina/memo/interpreter.py
"""Memo intent interpreter — hybrid pattern match + LLM fallback."""

import json
import re
from dataclasses import dataclass
from datetime import datetime

_KEYWORD = "memo"

_REMINDER_KEYWORDS: dict[str, set[str]] = {
    "pt": {"me lembra", "me lembre", "me avisa", "me avise", "me notifica",
           "me notifique", "não esquece", "não esquecer", "lembrete"},
    "en": {"remind me", "remember", "don't forget", "reminder", "notify me"},
}

_ACTION_WORDS: dict[str, dict[str, set[str]]] = {
    "pt": {
        "list":    {"quais", "liste", "listar", "mostre", "mostrar", "ver", "veja",
                    "exibir", "exiba"},
        "close":   {"feche", "fechar", "fecha", "concluir", "conclua",
                    "marque como feito", "completa"},
        "dismiss": {"descarte", "descartar", "descarta", "ignorar"},
        "create":  {"crie", "criar", "cria", "adicione", "novo", "nova", "salve", "salvar"},
    },
    "en": {
        "list":    {"list", "show", "display"},
        "close":   {"close", "done", "complete", "mark as done"},
        "dismiss": {"dismiss", "ignore"},
        "create":  {"add", "new", "save"},
    },
}

_FILLER: dict[str, set[str]] = {
    "pt": {"para mim"} | {w for ws in _ACTION_WORDS["pt"].values() for w in ws},
    "en": {"for me"}   | {w for ws in _ACTION_WORDS["en"].values() for w in ws},
}

_SYSTEM_PROMPT = """\
You are a command parser for the memo domain in a personal assistant.
The user message may be in Portuguese or English.
If provided, the first line is [now: YYYY-MM-DD HH:MM weekday] — use it to resolve relative dates.
Return JSON only — no explanation, no markdown.
Schema: {"action": "list|close|dismiss|create|remind|none", "subject": "<memo text or id>", "due_date": "<YYYY-MM-DD HH:MM or null>"}
Actions:
  list    — show open memos (subject may be empty)
  close   — mark a memo as done
  dismiss — discard/ignore a memo
  create  — save a new memo (no specific date)
  remind  — save a memo with a target date/time; extract subject and resolve due_date to YYYY-MM-DD HH:MM
  none    — not a memo action
If unsure, return {"action": "none"}.
"""


@dataclass
class MemoIntent:
    action: str         # "close" | "dismiss" | "create" | "list" | "remind" | "none"
    subject: str = ""   # memo text or partial id
    due_date: str = ""  # YYYY-MM-DD HH:MM (only for remind)


def has_reminder_context(text: str, lang: str = "pt") -> bool:
    """Keyword gate for reminder intent — no LLM."""
    lower = text.lower()
    return any(kw in lower for kw in _REMINDER_KEYWORDS.get(lang, _REMINDER_KEYWORDS["pt"]))


def try_action(text: str, lang: str = "pt") -> MemoIntent | None:
    """Layer 1 — pattern match. Returns MemoIntent or None (no LLM)."""
    lower = text.lower()
    if _KEYWORD not in lower:
        return None

    words_by_action = _ACTION_WORDS.get(lang, _ACTION_WORDS["pt"])
    for action, words in words_by_action.items():
        if any(w in lower for w in words):
            if action == "list":
                return MemoIntent(action="list")
            subject = _extract_subject(text, lang)
            if subject:
                return MemoIntent(action=action, subject=subject)

    return None


def interpret(text: str, llm, lang: str = "pt", now: datetime | None = None) -> MemoIntent:
    """Layer 2 — LLM fallback. Returns MemoIntent (action may be 'none')."""
    has_memo = _KEYWORD in text.lower()
    has_remind = has_reminder_context(text, lang)
    if not has_memo and not has_remind:
        return MemoIntent(action="none")
    try:
        if now is not None:
            weekday = now.strftime("%A")
            stamped = f"[now: {now.strftime('%Y-%m-%d %H:%M')} {weekday}]\n{text}"
        else:
            stamped = text
        raw = llm.complete(stamped, system=_SYSTEM_PROMPT)
        data = json.loads(raw)
        return MemoIntent(
            action=data.get("action", "none"),
            subject=data.get("subject", ""),
            due_date=data.get("due_date") or "",
        )
    except Exception:
        return MemoIntent(action="none")


def _extract_subject(text: str, lang: str = "pt") -> str:
    """Quoted text wins; otherwise extract fragment after 'memo' keyword."""
    quoted = re.search(r'["\'](.+?)["\']', text)
    if quoted:
        return quoted.group(1).strip()

    lower = text.lower()
    after = re.split(r'\bmemo\b', lower, maxsplit=1)
    if len(after) < 2:
        return ""
    fragment = after[1].strip()
    filler = _FILLER.get(lang, _FILLER["pt"])
    for w in sorted(filler, key=len, reverse=True):
        fragment = re.sub(rf'\b{re.escape(w)}\b', "", fragment).strip()
    return fragment.strip(' "\'')
