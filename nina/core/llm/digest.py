# nina/llm/digest.py
"""LLM-powered digest — summarises emails and calendar events."""

from dataclasses import dataclass

from nina.core.llm.client import LLMClient
from nina.integrations.google.calendar.client import Event
from nina.integrations.google.gmail.client import Message

_SYSTEM = (
    "Você é a Nina, uma assistente pessoal concisa e direta. "
    "Responda sempre em português do Brasil. "
    "Seja breve: use marcadores curtos, sem introduções longas."
)


@dataclass
class DigestResult:
    """Output of a digest run."""

    emails_summary: str
    events_summary: str
    combined_brief: str


def _format_emails(messages: list[Message]) -> str:
    if not messages:
        return "(nenhum email)"
    lines = []
    for m in messages:
        status = "NÃO LIDO" if not m.is_read else "lido"
        lines.append(
            f"- [{status}] De: {m.sender} | Assunto: {m.subject} | Preview: {m.snippet[:100]}"
        )
    return "\n".join(lines)


def _format_events(events: list[Event]) -> str:
    if not events:
        return "(nenhum evento)"
    lines = []
    for ev in events:
        loc = f" | Local: {ev.location}" if ev.location else ""
        lines.append(f"- {ev.start} — {ev.title}{loc}")
    return "\n".join(lines)


def summarise_emails(messages: list[Message], client: LLMClient) -> str:
    """Return a short LLM summary of the given email list."""
    prompt = (
        "Estes são os emails recentes:\n\n"
        f"{_format_emails(messages)}\n\n"
        "Resuma em até 5 marcadores o que precisa de atenção. "
        "Indique claramente os não lidos e qualquer urgência percebida."
    )
    return client.complete(prompt, system=_SYSTEM)


def summarise_events(events: list[Event], client: LLMClient) -> str:
    """Return a short LLM summary of the given event list."""
    prompt = (
        "Estes são os próximos eventos da agenda:\n\n"
        f"{_format_events(events)}\n\n"
        "Resuma em até 5 marcadores os pontos mais importantes. "
        "Destaque conflitos de horário ou eventos que exijam preparação."
    )
    return client.complete(prompt, system=_SYSTEM)


def daily_brief(
    messages: list[Message],
    events: list[Event],
    client: LLMClient,
) -> DigestResult:
    """Generate a full daily brief combining emails and calendar events."""
    emails_summary = summarise_emails(messages, client)
    events_summary = summarise_events(events, client)

    combined_prompt = (
        "Com base nos emails e na agenda abaixo, gere um briefing diário conciso.\n\n"
        "## Emails\n"
        f"{_format_emails(messages)}\n\n"
        "## Agenda\n"
        f"{_format_events(events)}\n\n"
        "Estruture a resposta em:\n"
        "1. **Prioridade imediata** — o que precisa de ação hoje\n"
        "2. **Agenda do dia** — resumo dos compromissos\n"
        "3. **Para não esquecer** — lembretes relevantes\n"
        "Seja direto, máximo 10 linhas no total."
    )
    combined_brief = client.complete(combined_prompt, system=_SYSTEM)

    return DigestResult(
        emails_summary=emails_summary,
        events_summary=events_summary,
        combined_brief=combined_brief,
    )
