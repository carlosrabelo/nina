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
        "teach":   {"ensine", "ensinar", "gravar", "salvar", "aplique", "aplicar",
                    "crie a label", "adicionar label", "adiciona label"},
        "rule_add": {"adicionar regra", "criar regra", "nova regra",
                     "associar label", "mapear remetente"},
        "move":    {"mover", "mova", "mudar", "mude", "renomear", "renomeie",
                    "trocar label", "troca label", "migrar label",
                    "rule move"},
    },
    "en": {
        "list":    {"list", "show", "display", "pending", "suggestions"},
        "dismiss": {"dismiss", "ignore", "discard"},
        "dismiss_all": {"dismiss all", "clear all", "discard all", "ignore all"},
        "teach":   {"teach", "save", "apply", "create label", "add label"},
        "rule_add": {"add rule", "create rule", "new rule", "map sender"},
        "move":    {"move", "rename", "migrate", "change label", "rule move"},
    },
}

_SYSTEM_PROMPT = """\
You are a command parser for the gmail_label domain in a personal assistant.
The user message may be in Portuguese or English.
Return JSON only — no explanation, no markdown.
Schema: {"action": "list|teach|dismiss|dismiss_all|rule_add|move|none", "target_id": "<suggestion id prefix or empty>", "label_name": "<label string or empty>", "sender": "<email address or empty>", "account": "<gmail account or empty>", "old_label": "<old label or empty>", "new_label": "<new label or empty>"}
Actions:
  list        — show open email suggestions
  dismiss     — ignore a single email suggestion (requires target_id)
  dismiss_all — ignore ALL open email suggestions at once
  teach       — teach/save a label for an email suggestion (label_name must start with @ or !)
  rule_add    — add a sender rule manually (requires account, sender, label_name starting with @ or !)
  move        — move all rules from one label to another (requires old_label and new_label, both starting with @ or !; optional account)
  none        — not a gmail_label action

Extraction Rules:
- target_id: usually an 8+ character alphanumeric string after the action or the word "id".
- label_name: the label to assign. Must start with "@" or "!". Do not include the word "label" or "etiqueta".
- sender: an email address (e.g. "newsletter@company.com") when creating a rule directly.
- account: the Gmail account (e.g. "user@gmail.com") when creating a rule directly.
- old_label: the source label when moving/renaming. Must start with "@" or "!".
- new_label: the destination label when moving/renaming. Must start with "@" or "!".

Examples:
- "ensine a label @Financeiro para o id a1b2c3d4" -> {"action": "teach", "target_id": "a1b2c3d4", "label_name": "@Financeiro", "sender": "", "account": "", "old_label": "", "new_label": ""}
- "ignora a sugestão a1b2c3d4" -> {"action": "dismiss", "target_id": "a1b2c3d4", "label_name": "", "sender": "", "account": "", "old_label": "", "new_label": ""}
- "listar emails pendentes" -> {"action": "list", "target_id": "", "label_name": "", "sender": "", "account": "", "old_label": "", "new_label": ""}
- "descartar todas as sugestões" -> {"action": "dismiss_all", "target_id": "", "label_name": "", "sender": "", "account": "", "old_label": "", "new_label": ""}
- "adicionar regra para newsletter@empresa.com com label @Marketing na conta user@gmail.com" -> {"action": "rule_add", "target_id": "", "label_name": "@Marketing", "sender": "newsletter@empresa.com", "account": "user@gmail.com", "old_label": "", "new_label": ""}
- "move @sane-later/google para !google" -> {"action": "move", "target_id": "", "label_name": "", "sender": "", "account": "", "old_label": "@sane-later/google", "new_label": "!google"}
- "mover etiqueta @Finance para @Financeiro" -> {"action": "move", "target_id": "", "label_name": "", "sender": "", "account": "", "old_label": "@Finance", "new_label": "@Financeiro"}

If unsure, return {"action": "none"}.
"""


@dataclass
class EmailLabelIntent:
    action: str         # "list" | "teach" | "dismiss" | "dismiss_all" | "rule_add" | "move" | "none"
    target_id: str = ""
    label_name: str = ""
    sender: str = ""
    account: str = ""
    old_label: str = ""
    new_label: str = ""


def try_action(text: str, lang: str = "pt") -> EmailLabelIntent | None:
    """Layer 1 — pattern match. Returns EmailLabelIntent or None (no LLM)."""
    lower = text.lower()
    if not any(kw in lower for kw in _KEYWORDS):
        return None

    words_by_action = _ACTION_WORDS.get(lang, _ACTION_WORDS["pt"])

    # 1. dismiss all (must be before dismiss single)
    if any(w in lower for w in words_by_action["dismiss_all"]):
        return EmailLabelIntent(action="dismiss_all")

    # 2. move (needs old_label and new_label) — before list because "mover" contains "ver"
    if any(w in lower for w in words_by_action["move"]):
        labels_m = re.findall(r'([@!][\w/-]+)', text)
        if len(labels_m) >= 2:
            return EmailLabelIntent(
                action="move",
                old_label=labels_m[0],
                new_label=labels_m[1],
            )

    # 3. rule add (needs account, sender, label)
    if any(w in lower for w in words_by_action["rule_add"]):
        label_m = re.search(r'([@!][\w/-]+)', text)
        email_m = re.search(r'[\w.+-]+@[\w.-]+\.\w+', text)
        if label_m and email_m:
            return EmailLabelIntent(
                action="rule_add",
                label_name=label_m.group(1),
                sender=email_m.group(0),
            )

    # 4. dismiss single
    if any(w in lower for w in words_by_action["dismiss"]):
        m = re.search(r'\b([a-f0-9]{8,})\b', lower)
        if m:
            return EmailLabelIntent(action="dismiss", target_id=m.group(1))

    # 5. teach
    if any(w in lower for w in words_by_action["teach"]):
        m = re.search(r'\b([a-f0-9]{8,})\b\s+(?:para\s+)?(?:a\s+)?(?:label|etiqueta\s+)?(@?[\w/-]+)', lower)
        if m:
            return EmailLabelIntent(action="teach", target_id=m.group(1), label_name=m.group(2))

    # 6. list (fallback)
    if any(w in lower for w in words_by_action["list"]):
        if not re.search(r'\b[a-f0-9]{8,}\b', lower):
            return EmailLabelIntent(action="list")

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
            sender=data.get("sender", ""),
            account=data.get("account", ""),
            old_label=data.get("old_label", ""),
            new_label=data.get("new_label", ""),
        )
    except Exception:
        return EmailLabelIntent(action="none")
