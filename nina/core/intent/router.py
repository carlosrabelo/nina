"""Unified intent router — local patterns first, LLM fallback.

Routing pipeline (4 layers):
  Layer 1: Per-skill keyword gate (try_action) — zero LLM
  Layer 2: local_router — advanced regex patterns + entity extraction — zero LLM
  Layer 3: LLM-based RouterIntent — classifies domain + extracts entities
  Layer 4: Dedicated interpreters (blocking, workdays) — second LLM call

Simple domains (presence, memo, calendar, notifications, profile) are fully resolved
by Layer 2 when patterns match. Complex domains (blocking, workdays) fall through
to Layer 4 for dedicated LLM interpretation.
"""
# ruff: noqa: E501 — _SYSTEM_PROMPT lines are LLM prompts, not code

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nina.core.intent.local_router import LocalIntent
from nina.core.intent.local_router import route as local_route

_VALID_DOMAINS = {
    "memo",
    "calendar",
    "blocking",
    "presence",
    "workdays",
    "profile",
    "notifications",
    "activity_log",
    "gmail_label",
    "none",
}

_SYSTEM_PROMPT = """\
You are the intent engine for a bilingual (Portuguese/English) personal assistant.
If provided, the first line is [now: YYYY-MM-DD HH:MM weekday] — use it to resolve relative dates/times.
Return ONLY a single JSON object — no explanation, no markdown.

━━━ OUTPUT SCHEMA ━━━
{
  "domain":   "presence|memo|calendar|notifications|profile|blocking|workdays|gmail_label|none",
  "action":   "<domain-specific action — see below>",

  // presence only
  "status":   "home|work|out|dnd",
  "note":     "<brief context extracted from the message, same language as input>",

  // memo only
  "subject":  "<memo text or partial id>",
  "due_date": "<YYYY-MM-DD HH:MM resolved from text, or null>",

  // notifications only
  "minutes":  <int or null>,
  "days":     <int or null>,

  // profile only
  "updates":  [{"presence": "home|work|out|dnd", "gmail": ["..."], "calendar": ["..."]}],

  // calendar only (read — never create events here)
  "calendar_window": "upcoming|today|tomorrow|week|days",
  "calendar_span_days": <int or null>,
  "calendar_keyword": "<substring or null>",
  "calendar_period": "full|morning|afternoon",
  "calendar_on_date": "<YYYY-MM-DD or null>",

  // gmail_label only
  "target_id": "<suggestion id prefix or empty>",
  "label_name": "<Gmail label to assign or empty>"
}

Fields not relevant to the detected domain must be null / "" / [].

━━━ DOMAINS ━━━

▸ presence — user reports their current location or status
  action: set_presence
  status: home (at home / working from home),
          work (at the office, campus, client site, any in-person work location),
          out (outside, errands, lunch, traveling),
          dnd (meeting, course, training, presentation, focused work, busy)
  note: extract a brief label from the message (e.g. "almoço", "reunião", "treinamento")
  Examples:
    "estou em casa"                 → presence, set_presence, home
    "cheguei no trabalho"           → presence, set_presence, work
    "acabei de chegar no escritório"→ presence, set_presence, work
    "cheguei no campus"             → presence, set_presence, work,  note="campus"
    "estou no cliente"              → presence, set_presence, work,  note="cliente"
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

▸ calendar — read-only: list agenda, search events, or check when you are free (does NOT create events — use blocking for that)
  action: list | search | free_busy
  calendar_window: upcoming | today | tomorrow | week | days (default upcoming for list/search)
  calendar_span_days: int or null — with calendar_window=days (e.g. next 5 days → 5); for week default 7
  calendar_keyword: string or null — substring search in title/location
  calendar_period: full | morning | afternoon — narrow today/tomorrow or free_busy questions
  calendar_on_date: "YYYY-MM-DD" or null — specific calendar day if user names a date
  Examples:
    "quais meus eventos" → calendar, list, calendar_window=upcoming
    "o que tenho hoje" → calendar, list, calendar_window=today
    "eventos com dentista" → calendar, search, calendar_keyword=dentist
    "estou livre amanhã à tarde" → calendar, free_busy, calendar_window=tomorrow, calendar_period=afternoon
    "am I free tomorrow morning" → calendar, free_busy, calendar_window=tomorrow, calendar_period=morning

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
    "no escritório usar work@co.com"       → profile, update_profile, updates=[{work, gmail=[work@co.com]}]
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

▸ gmail_label — managing Gmail label learning (listing suggestions, teaching labels, ignoring senders)
  action: list   (show open sender→label suggestions)
          teach  (assign a Gmail label to a pending sender)
          dismiss (ignore a suggestion and block future suggestions for that sender)
  target_id: the suggestion id prefix (8+ hex chars) or empty for list
  label_name: the Gmail label to assign (teach only), e.g. "@Financeiro", "Trabalho"
  Examples:
    "quais sugestoes de email"                    → gmail_label, list
    "listar etiquetas pendentes"                  → gmail_label, list
    "mostra as sugestoes de remetente"            → gmail_label, list
    "ensina a etiqueta @Financeiro para abc12345" → gmail_label, teach, target_id="abc12345", label_name="@Financeiro"
    "ignora a sugestao abc12345"                  → gmail_label, dismiss, target_id="abc12345"
    "descarta o remetente abc12345"               → gmail_label, dismiss, target_id="abc12345"

━━━ DISAMBIGUATION RULES ━━━
• "estou no trabalho" / "cheguei no trabalho"  → presence (current status), NOT workdays
• "trabalho de segunda a sexta"                 → workdays (schedule change), NOT presence
• "vou trabalhar de casa hoje"                  → presence home (current status), NOT workdays
• "em reunião" without explicit time/duration   → presence dnd, NOT blocking
• "agenda reunião às 15h" / "marcar na agenda às 15h" / "schedule meeting at 3pm" → blocking (creates calendar time — has explicit time)
• "estou livre amanhã" / "am I free tomorrow" → calendar free_busy (read-only), NOT blocking
• When in doubt between blocking and presence: if there's an explicit time → blocking, otherwise → presence dnd
"""


@dataclass
class RouterIntent:
    domain: str  # one of _VALID_DOMAINS
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
    # calendar (read)
    calendar_window: str = ""
    calendar_span_days: int | None = None
    calendar_keyword: str = ""
    calendar_period: str = ""
    calendar_on_date: str = ""
    # gmail_label
    target_id: str = ""
    label_name: str = ""
    # meta
    resolved_by: str = "llm"  # "local" | "llm" | "none"


def _json_int_calendar(v: Any) -> int | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        return int(v.strip())
    return None


def _local_to_router(local: LocalIntent) -> RouterIntent:
    """Convert a LocalIntent to a RouterIntent."""
    entities = local.entities
    return RouterIntent(
        domain=local.domain,
        action=local.action,
        status=entities.get("status", ""),
        note=entities.get("note", ""),
        subject=entities.get("subject", ""),
        due_date=entities.get("due_date", ""),
        minutes=entities.get("minutes"),
        days=entities.get("days"),
        calendar_window=str(entities.get("calendar_window", "") or ""),
        calendar_span_days=_json_int_calendar(entities.get("calendar_span_days")),
        calendar_keyword=str(entities.get("calendar_keyword", "") or ""),
        calendar_period=str(entities.get("calendar_period", "") or ""),
        calendar_on_date=str(entities.get("calendar_on_date", "") or ""),
        target_id=str(entities.get("target_id", "") or ""),
        label_name=str(entities.get("label_name", "") or ""),
        resolved_by="local",
    )


def route(
    text: str,
    llm,
    lang: str = "pt",
    now: datetime | None = None,
) -> RouterIntent:
    """Route intent through local patterns first, then LLM fallback.

    Returns RouterIntent with resolved_by indicating which layer resolved it.
    """
    # ── Layer 2: Local pattern matching ───────────────────────────────────
    local = local_route(text, lang, now)
    if local is not None:
        return _local_to_router(local)

    # ── Layer 3: LLM-based routing ────────────────────────────────────────
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
        return RouterIntent(domain="none", resolved_by="none")

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
        calendar_window=str(data.get("calendar_window") or ""),
        calendar_span_days=_json_int_calendar(data.get("calendar_span_days")),
        calendar_keyword=str(data.get("calendar_keyword") or ""),
        calendar_period=str(data.get("calendar_period") or ""),
        calendar_on_date=str(data.get("calendar_on_date") or ""),
        target_id=str(data.get("target_id") or ""),
        label_name=str(data.get("label_name") or ""),
        resolved_by="llm",
    )
