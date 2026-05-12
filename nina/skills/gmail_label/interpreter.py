"""Gmail Label intent interpreter — hybrid pattern match + LLM fallback."""

import json
import re
from dataclasses import dataclass

_KEYWORDS = {"email", "e-mail", "label", "etiqueta", "gmail_label"}

_ACTION_WORDS: dict[str, dict[str, set[str]]] = {
    "pt": {
        "list":    {"quais", "liste", "listar", "mostre", "mostrar", "ver", "veja",
                    "exibir", "exiba", "pendentes", "pendências", "sugestões", "sugestoes"},
        "dismiss": {"descarte", "descartar", "descarta", "ignorar", "ignore", "dispensar"},
        "dismiss_all": {"descartar todas", "descarte todas", "ignorar todas", "ignore todas",
                        "descartar tudo", "descarte tudo", "ignorar tudo", "ignore tudo",
                        "apagar todas", "apague todas", "limpar sugestões", "limpar sugestoes",
                        "limpar pendentes"},
        "teach":   {"ensine", "ensinar", "gravar", "salvar", "aplique", "aplicar", "crie a label", "adicionar label", "adiciona label"},
    },
    "en": {
        "list":    {"list", "show", "display", "pending", "suggestions"},
        "dismiss": {"dismiss", "ignore", "discard"},
        "dismiss_all": {"dismiss all", "clear all", "discard all", "ignore all"},
        "teach":   {"teach", "save", "apply", "create label", "add label"},
    },
}

_SYSTEM_PROMPT = """\
You are a command parser for the gmail_label domain in a personal assistant.
The user message may be in Portuguese or English.
Return JSON only — no explanation, no markdown.
Schema: {"action": "list|teach|dismiss|dismiss_all|none", "target_id": "<suggestion id prefix or empty>", "label_name": "<label string or empty>"}
Actions:
  list        — show open email suggestions
  dismiss     — ignore a single email suggestion (requires target_id)
  dismiss_all — ignore ALL open email suggestions at once (target_id and label_name are empty)
  teach       — teach/save a label for an email suggestion (label_name must start with @)
  none        — not a gmail_label action

Extraction Rules:
- target_id: usually an 8+ character alphanumeric string (e.g., "1234abcd") that comes after the action or the word "id".
- label_name: the name of the label they want to assign. Must start with "@". Do not include the word "label" or "etiqueta" in the label name itself.

Examples:
- "ensine a label @Financeiro para o id a1b2c3d4" -> {"action": "teach", "target_id": "a1b2c3d4", "label_name": "@Financeiro"}
- "ignora a sugestão a1b2c3d4" -> {"action": "dismiss", "target_id": "a1b2c3d4", "label_name": ""}
- "listar emails pendentes" -> {"action": "list", "target_id": "", "label_name": ""}
- "descartar todas as sugestões" -> {"action": "dismiss_all", "target_id": "", "label_name": ""}
- "apagar todos os pendentes" -> {"action": "dismiss_all", "target_id": "", "label_name": ""}
- "dismiss all suggestions" -> {"action": "dismiss_all", "target_id": "", "label_name": ""}

If unsure, return {"action": "none"}.
"""


@dataclass
class EmailLabelIntent:
    action: str         # "list" | "teach" | "dismiss" | "none"
    target_id: str = "" # minimum 8 characters usually
    label_name: str = ""


def try_action(text: str, lang: str = "pt") -> EmailLabelIntent | None:
    """Layer 1 — pattern match. Returns EmailLabelIntent or None (no LLM)."""
    lower = text.lower()
    if not any(kw in lower for kw in _KEYWORDS):
        return None

    words_by_action = _ACTION_WORDS.get(lang, _ACTION_WORDS["pt"])

    # 1. list
    if any(w in lower for w in words_by_action["list"]):
        # If it doesn't mention specific ids, it's likely a list
        if not re.search(r'\b[a-f0-9]{8,}\b', lower):
            return EmailLabelIntent(action="list")

    # 2. dismiss all
    if any(w in lower for w in words_by_action["dismiss_all"]):
        return EmailLabelIntent(action="dismiss_all")

    # 3. dismiss single
    if any(w in lower for w in words_by_action["dismiss"]):
        # Extract potential ID (hex string 8+ chars)
        m = re.search(r'\b([a-f0-9]{8,})\b', lower)
        if m:
            return EmailLabelIntent(action="dismiss", target_id=m.group(1))

    # 3. teach
    # Needs LLM for accurate target_id and label_name extraction usually,
    # but we can try a basic regex for "teach <id> <label>"
    if any(w in lower for w in words_by_action["teach"]):
        m = re.search(r'\b([a-f0-9]{8,})\b\s+(?:para\s+)?(?:a\s+)?(?:label|etiqueta\s+)?(@?[\w/-]+)', lower)
        if m:
            return EmailLabelIntent(action="teach", target_id=m.group(1), label_name=m.group(2))

    return None


def interpret(text: str, llm, lang: str = "pt") -> EmailLabelIntent:
    """Layer 2 — LLM fallback. Returns EmailLabelIntent (action may be 'none')."""
    if not any(kw in text.lower() for kw in _KEYWORDS):
        return EmailLabelIntent(action="none")
    try:
        raw = llm.complete(text, system=_SYSTEM_PROMPT)
        # Clean any markdown formatting if present
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(raw)
        return EmailLabelIntent(
            action=data.get("action", "none"),
            target_id=data.get("target_id", ""),
            label_name=data.get("label_name", ""),
        )
    except Exception:
        return EmailLabelIntent(action="none")
