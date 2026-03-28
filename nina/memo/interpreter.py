# nina/memo/interpreter.py
"""Memo intent interpreter — hybrid pattern match + LLM fallback."""

import json
import re
from dataclasses import dataclass

_KEYWORD = "memo"

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
Return JSON only — no explanation, no markdown.
Schema: {"action": "list|close|dismiss|create|none", "subject": "<memo text or id>"}
Actions:
  list    — show open memos (subject may be empty)
  close   — mark a memo as done
  dismiss — discard/ignore a memo
  create  — save a new memo
  none    — not a memo action
If unsure, return {"action": "none"}.
"""


@dataclass
class MemoIntent:
    action: str         # "close" | "dismiss" | "create" | "list" | "none"
    subject: str = ""   # memo text or partial id


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


def interpret(text: str, llm) -> MemoIntent:
    """Layer 2 — LLM fallback. Returns MemoIntent (action may be 'none')."""
    if _KEYWORD not in text.lower():
        return MemoIntent(action="none")
    try:
        raw = llm.complete(text, system=_SYSTEM_PROMPT)
        data = json.loads(raw)
        return MemoIntent(
            action=data.get("action", "none"),
            subject=data.get("subject", ""),
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
