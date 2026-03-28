# nina/obsidian/interpreter.py
"""Obsidian intent interpreter — pattern match only, no LLM needed."""

from dataclasses import dataclass

_KEYWORDS: dict[str, set[str]] = {
    "pt": {"obsidian", "vault", "sincroniza", "sincronizar", "sincronização",
           "atualiza o obsidian", "atualizar obsidian"},
    "en": {"obsidian", "vault", "synchronize"},
}


@dataclass
class ObsidianIntent:
    action: str  # "sync" | "none"


def has_context(text: str, lang: str = "pt") -> bool:
    """Keyword gate — no LLM."""
    lower = text.lower()
    return any(kw in lower for kw in _KEYWORDS.get(lang, _KEYWORDS["pt"]))


def try_action(text: str, lang: str = "pt") -> ObsidianIntent | None:
    """Layer 1 — pattern match. Returns ObsidianIntent or None."""
    if not has_context(text, lang):
        return None
    return ObsidianIntent(action="sync")
