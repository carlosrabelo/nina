"""Unified intent router — classifies domain AND extracts entities in one LLM call.

Simple domains (presence, memo, calendar, notifications, profile) are fully resolved
here, so no second interpreter call is needed. Complex domains (blocking, workdays)
return only the domain; their dedicated interpreters handle entity extraction.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

_VALID_DOMAINS = {
    "memo", "calendar", "blocking", "presence", "workdays",
    "profile", "notifications", "none",
}

_SYSTEM_PROMPT = """\
You are the intent engine for a bilingual (Portuguese/English) personal assistant.
If provided, the first line is [now: YYYY-MM-DD HH:MM weekday] — use it to resolve relative dates/times.
Return ONLY a single JSON object — no explanation, no markdown.

━━━ OUTPUT SCHEMA ━━━
{
  "domain":   "presence|memo|calendar|notifications|profile|blocking|workdays|none",
  "action":   "<domain-specific action — see below>",

  // presence only
  "status":   "home|office|out|dnd",
  "note":     "<brief context extracted from the message, same language as input>",

  // memo only
  "subject":  "<memo text or partial id>",
  "due_date": "<YYYY-MM-DD HH:MM resolved from text, or null>",

  // notifications only
  "minutes":  <int or null>,
  "days":     <int or null>,

  // profile only
  "updates":  [{"presence": "home|office|out|dnd", "gmail": ["..."], "calendar": ["..."]}]
}

Fields not relevant to the detected domain must be null / "" / [].

━━━ DOMAINS ━━━

▸ presence — user reports their current location or status
  action: set_presence
  status: home (at home / working from home),
          office (at the office / arrived at work),
          out (outside, errands, lunch, traveling),
          dnd (meeting, course, training, presentation, focused work, busy)
  note: extract a brief label from the message (e.g. "almoço", "reunião", "treinamento")
  Examples:
    "estou em casa"                 → presence, set_presence, home
    "cheguei no trabalho"           → presence, set_presence, office
    "acabei de chegar no escritório"→ presence, set_presence, office
    "saindo para o almoço"          → presence, set_presence, out,  note="almoço"
    "em reunião com Sandra"         → presence, set_presence, dnd,  note="reunião com Sandra"
    "estou num treinamento"         → presence, set_presence, dnd,  note="treinamento"
    "foco, não me interrompa"       → presence, set_presence, dnd,  note="foco"

▸ memo — notes, reminders, tasks
  action: create  (save a plain note — no date)
          remind  (save a note with a due date/time — resolve due_date absolutely)
          close   (mark a memo as done)
          dismiss (discard/ignore a memo)
          list    (show open memos)
  subject: the memo text (create/remind/close/dismiss) or empty (list)
  due_date: resolved YYYY-MM-DD HH:MM (remind only); null for all other actions
  Examples:
    "memo comprar pão"                     → memo, create, subject="comprar pão"
    "me lembra de ligar amanhã às 10h"     → memo, remind, subject="ligar", due_date="2026-03-31 10:00"
    "feche o memo reunião"                 → memo, close,  subject="reunião"
    "descarte o memo compras"              → memo, dismiss, subject="compras"
    "memos" or "quais meus memos"          → memo, list

▸ calendar — listing upcoming events (read-only)
  action: list
  Examples:
    "quais meus eventos", "o que tenho hoje", "minha agenda"

▸ notifications — reminder timing configuration
  action: set_reminder  (minutes before event — populate minutes)
          set_days      (days ahead to watch — populate days)
          get           (show current settings)
  Examples:
    "me avisa 30 minutos antes"            → notifications, set_reminder, minutes=30
    "notificação com 2 dias de antecedência" → notifications, set_days, days=2
    "quais minhas notificações"            → notifications, get

▸ profile — linking email/calendar accounts to presence statuses
  action: update_profile
  updates: list of {presence, gmail: [], calendar: []}
  Examples:
    "no escritório usar work@co.com"       → profile, update_profile, updates=[{office, gmail=[work@co.com]}]
    "em casa uso pessoal@gmail.com"        → profile, update_profile, updates=[{home, gmail=[pessoal@gmail.com], calendar=[pessoal@gmail.com]}]

▸ blocking — blocking/scheduling time in the calendar
  Requires an explicit time reference ("às 14h", "amanhã", "por 1 hora", "próxima segunda")
  action: create
  Do NOT extract entities — just set domain=blocking, action=create.
  Examples:
    "estou em reunião com Sandra por 1 hora"
    "agenda dentista amanhã às 9h"
    "bloqueia de 14h às 15h30 para call"

▸ workdays — changing the work schedule or timezone (NOT current status)
  action: update_schedule
  Do NOT extract entities — just set domain=workdays, action=update_schedule.
  Examples:
    "trabalho de segunda a sexta das 9 às 18"
    "meu fuso horário é America/Cuiaba"
    "não trabalho às quartas"
    "sexta saio às 17h"

▸ none — not recognized or out of scope
  Examples: "qual é o tempo?", "conta uma piada", "o que é machine learning"

━━━ DISAMBIGUATION RULES ━━━
• "estou no trabalho" / "cheguei no trabalho"  → presence (current status), NOT workdays
• "trabalho de segunda a sexta"                 → workdays (schedule change), NOT presence
• "vou trabalhar de casa hoje"                  → presence home (current status), NOT workdays
• "em reunião" without explicit time/duration   → presence dnd, NOT blocking
• "agenda reunião às 15h"                       → blocking (has explicit time)
• When in doubt between blocking and presence: if there's an explicit time → blocking, otherwise → presence dnd
"""


@dataclass
class RouterIntent:
    domain: str                                      # one of _VALID_DOMAINS
    action: str = "none"
    # presence
    status: str = ""
    note: str = ""
    # memo
    subject: str = ""
    due_date: str = ""
    # notifications
    minutes: int | None = None
    days: int | None = None
    # profile
    updates: list[dict[str, Any]] = field(default_factory=list)


def route(text: str, llm, lang: str = "pt", now: datetime | None = None) -> RouterIntent:  # noqa: ARG001
    """One LLM call — returns domain + entities for simple domains.
    Complex domains (blocking, workdays) return only domain; their interpreters handle the rest."""
    try:
        if now is not None:
            weekday = now.strftime("%A")
            stamped = f"[now: {now.strftime('%Y-%m-%d %H:%M')} {weekday}]\n{text}"
        else:
            stamped = text

        raw = llm.complete(stamped, system=_SYSTEM_PROMPT)
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(raw)
    except Exception:
        return RouterIntent(domain="none")

    domain = data.get("domain", "none")
    if domain not in _VALID_DOMAINS:
        domain = "none"

    return RouterIntent(
        domain=domain,
        action=str(data.get("action") or "none"),
        status=str(data.get("status") or ""),
        note=str(data.get("note") or ""),
        subject=str(data.get("subject") or ""),
        due_date=str(data.get("due_date") or ""),
        minutes=data.get("minutes"),
        days=data.get("days"),
        updates=list(data.get("updates") or []),
    )
