# tests/test_digest.py
"""Unit tests for digest — LLM calls are mocked."""

from unittest.mock import MagicMock, create_autospec

import pytest

from nina.integrations.google.calendar.client import Event
from nina.core.llm.digest import DigestResult, daily_brief, summarise_emails, summarise_events
from nina.integrations.google.gmail.client import Message
from nina.core.llm.client import LLMClient


def _client(response: str = "resposta simulada") -> MagicMock:
    client = create_autospec(LLMClient, instance=True)
    client.complete.return_value = response
    return client


def _email(
    subject: str = "Assunto",
    sender: str = "remetente@ex.com",
    snippet: str = "Prévia do email",
    is_read: bool = False,
) -> Message:
    return Message(
        id="x", account="voce@gmail.com", subject=subject,
        sender=sender, date="27/03 09:00", snippet=snippet, is_read=is_read,
    )


def _event(
    title: str = "Reunião",
    start: str = "27/03 10:00",
    location: str = "",
) -> Event:
    return Event(
        id="e1", account="voce@gmail.com", title=title,
        start=start, end="27/03 11:00", location=location, calendar="primary",
    )


def test_summarise_emails_returns_llm_response():
    client = _client("• Email urgente do chefe")
    result = summarise_emails([_email()], client)
    assert result == "• Email urgente do chefe"
    client.complete.assert_called_once()


def test_summarise_emails_prompt_contains_subject():
    client = _client()
    summarise_emails([_email(subject="Fatura vencendo")], client)
    prompt = client.complete.call_args.args[0]
    assert "Fatura vencendo" in prompt


def test_summarise_emails_unread_flag_in_prompt():
    client = _client()
    summarise_emails([_email(is_read=False)], client)
    prompt = client.complete.call_args.args[0]
    assert "NÃO LIDO" in prompt


def test_summarise_emails_read_flag_in_prompt():
    client = _client()
    summarise_emails([_email(is_read=True)], client)
    prompt = client.complete.call_args.args[0]
    assert "lido" in prompt


def test_summarise_emails_empty_list():
    client = _client()
    summarise_emails([], client)
    prompt = client.complete.call_args.args[0]
    assert "nenhum email" in prompt


def test_summarise_events_returns_llm_response():
    client = _client("• Reunião às 10h")
    result = summarise_events([_event()], client)
    assert result == "• Reunião às 10h"
    client.complete.assert_called_once()


def test_summarise_events_prompt_contains_title():
    client = _client()
    summarise_events([_event(title="Deploy em produção")], client)
    prompt = client.complete.call_args.args[0]
    assert "Deploy em produção" in prompt


def test_summarise_events_location_included_when_present():
    client = _client()
    summarise_events([_event(location="Sala 3")], client)
    prompt = client.complete.call_args.args[0]
    assert "Sala 3" in prompt


def test_summarise_events_empty_list():
    client = _client()
    summarise_events([], client)
    prompt = client.complete.call_args.args[0]
    assert "nenhum evento" in prompt


def test_daily_brief_returns_digest_result():
    client = _client("resumo")
    result = daily_brief([_email()], [_event()], client)
    assert isinstance(result, DigestResult)


def test_daily_brief_calls_llm_three_times():
    client = _client("ok")
    daily_brief([_email()], [_event()], client)
    assert client.complete.call_count == 3


def test_daily_brief_combined_contains_both_sections():
    client = _client("ok")
    daily_brief([_email(subject="Urgente")], [_event(title="Dentista")], client)
    combined_prompt = client.complete.call_args_list[2].args[0]
    assert "Urgente" in combined_prompt
    assert "Dentista" in combined_prompt


def test_daily_brief_fields_match_llm_responses():
    responses = ["resumo emails", "resumo eventos", "briefing completo"]
    client = create_autospec(LLMClient, instance=True)
    client.complete.side_effect = responses
    result = daily_brief([_email()], [_event()], client)
    assert result.emails_summary == "resumo emails"
    assert result.events_summary == "resumo eventos"
    assert result.combined_brief == "briefing completo"
