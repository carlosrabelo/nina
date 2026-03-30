"""Daily digest demo — uses real Gmail/Calendar data when available."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from nina.errors import AuthError, CalendarError, ConfigError, GmailError, LLMError
from nina.integrations.google.auth import discover_accounts
from nina.integrations.google.calendar.client import CalendarClient, Event
from nina.integrations.google.gmail.client import GmailMultiClient, Message
from nina.core.llm.client import LLMClient
from nina.core.llm.digest import daily_brief

load_dotenv()

# ── Fallback simulated data ───────────────────────────────────────────────────

_FAKE_EMAILS: list[Message] = [
    Message(
        id="1", account="voce@gmail.com",
        subject="Reunião de alinhamento — amanhã 10h",
        sender="chefe@empresa.com", date="hoje 08:14",
        snippet="Preciso que você apresente os resultados do Q1. Por favor confirme presença até hoje às 18h.",
        is_read=False,
    ),
    Message(
        id="2", account="voce@gmail.com",
        subject="Fatura vencendo em 2 dias — Cartão Nubank",
        sender="noreply@nubank.com.br", date="hoje 07:00",
        snippet="Sua fatura de R$ 1.247,80 vence em 29/03. Pague até a data para evitar juros.",
        is_read=False,
    ),
    Message(
        id="3", account="voce@gmail.com",
        subject="PR #142 aprovado — deploy em produção",
        sender="github@github.com", date="ontem 22:30",
        snippet="carlos aprovou suas alterações. O merge foi realizado na branch main.",
        is_read=True,
    ),
    Message(
        id="4", account="voce@gmail.com",
        subject="Re: Proposta comercial — aguardando retorno",
        sender="cliente@startup.io", date="ontem 17:45",
        snippet="Analisamos a proposta e temos algumas dúvidas sobre o escopo. Podemos conversar sexta?",
        is_read=True,
    ),
    Message(
        id="5", account="trabalho@gmail.com",
        subject="[URGENT] Servidor de staging fora do ar",
        sender="alertas@monitoring.io", date="hoje 09:02",
        snippet="ALERTA CRÍTICO: o servidor staging-01 não responde há 15 minutos. Verifique imediatamente.",
        is_read=False,
    ),
]

_FAKE_EVENTS: list[Event] = [
    Event(id="e1", account="voce@gmail.com", title="Reunião de alinhamento Q1",
          start="amanhã 10:00", end="amanhã 11:00",
          location="Sala de reuniões 3 — andar 4", calendar="primary"),
    Event(id="e2", account="voce@gmail.com", title="1:1 com chefe",
          start="hoje 14:00", end="hoje 14:30",
          location="", calendar="primary"),
    Event(id="e3", account="voce@gmail.com", title="Dentista",
          start="hoje 18:00", end="hoje 19:00",
          location="Clínica Saúde — Av. Paulista 1000", calendar="primary"),
    Event(id="e4", account="voce@gmail.com", title="Deploy em produção — sistema de pagamentos",
          start="amanhã 22:00", end="amanhã 23:30",
          location="", calendar="primary"),
]


# ── Data loaders ──────────────────────────────────────────────────────────────

def _load_emails() -> tuple[list[Message], str]:
    try:
        nina = GmailMultiClient.from_env()
        messages: list[Message] = []
        for account in nina.accounts:
            messages.extend(nina.client(account).list_unread(max_results=10))
            messages.extend(nina.client(account).list_latest(max_results=5))
        seen: set[str] = set()
        unique = [m for m in messages if not (m.id in seen or seen.add(m.id))]  # type: ignore[func-returns-value]
        return unique, "Gmail (real)"
    except (ConfigError, AuthError, GmailError) as e:
        print(f"  Gmail indisponível ({e.__class__.__name__}) — usando dados simulados")
        return _FAKE_EMAILS, "simulado"


def _load_events() -> tuple[list[Event], str]:
    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    accounts = discover_accounts(tokens_dir)
    if not accounts:
        print("  Calendar indisponível (sem contas autenticadas) — usando dados simulados")
        return _FAKE_EVENTS, "simulado"

    events: list[Event] = []
    for account in accounts:
        try:
            events.extend(CalendarClient(account, tokens_dir).list_next_days(days=3))
        except (AuthError, CalendarError) as e:
            print(f"  Calendar erro em {account} ({e.__class__.__name__}) — ignorando")

    if not events:
        print("  Nenhum evento nos próximos 3 dias — usando dados simulados")
        return _FAKE_EVENTS, "simulado"

    return events, "Google Calendar — próximos 3 dias (todos os calendários)"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Carregando configuração do LLM...")
    try:
        client = LLMClient.from_env()
    except LLMError as e:
        print(f"\nErro: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Modelo : {client.model}\n")

    print("Carregando dados...")
    emails, email_src = _load_emails()
    events, event_src = _load_events()

    unread = sum(1 for m in emails if not m.is_read)
    print(f"  Emails  : {len(emails)} ({unread} não lidos) — {email_src}")
    print(f"  Eventos : {len(events)} — {event_src}")
    print()

    print("Gerando digest com o LLM...\n")
    try:
        result = daily_brief(emails, events, client)
    except LLMError as e:
        print(f"Erro ao chamar o LLM: {e}", file=sys.stderr)
        sys.exit(1)

    sep = "─" * 60

    print(sep)
    print("📧  EMAILS — resumo")
    print(sep)
    print(result.emails_summary)
    print()

    print(sep)
    print("📅  AGENDA — resumo")
    print(sep)
    print(result.events_summary)
    print()

    print(sep)
    print("🗒  BRIEFING DO DIA")
    print(sep)
    print(result.combined_brief)
    print()


if __name__ == "__main__":
    main()
