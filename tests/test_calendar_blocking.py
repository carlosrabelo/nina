# tests/test_calendar_blocking.py
"""Tests for the calendar blocking interpreter."""

from datetime import datetime
from unittest.mock import MagicMock

from nina.google.calendar.blocking import BlockingIntent, interpret


def _llm(response: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = response
    return llm


_NOW = datetime(2024, 1, 15, 13, 15)


class TestBlockingInterpreter:
    def test_single_event_now(self) -> None:
        payload = '[{"action": "block_calendar", "title": "Atendimento Sandra Mariotto", "duration_minutes": 60, "start_time": "13:15"}]'
        result = interpret("estou atendendo a professora Sandra Mariotto, devo levar uma hora", _llm(payload), now=_NOW)
        assert len(result) == 1
        assert result[0].action == "block_calendar"
        assert result[0].title == "Atendimento Sandra Mariotto"
        assert result[0].duration_minutes == 60
        assert result[0].start_time == "13:15"

    def test_two_events_in_one_message(self) -> None:
        payload = (
            '[{"action": "block_calendar", "title": "Reunião", "duration_minutes": 30, "start_time": "13:15"},'
            ' {"action": "block_calendar", "title": "Atendimento Vera Lucia", "duration_minutes": 60, "start_time": "16:00"}]'
        )
        result = interpret(
            "estou em reunião agora por 30 minutos e às 16:00 atendo a professora Vera Lucia por uma hora",
            _llm(payload), now=_NOW,
        )
        assert len(result) == 2
        assert result[0].title == "Reunião"
        assert result[0].start_time == "13:15"
        assert result[1].title == "Atendimento Vera Lucia"
        assert result[1].start_time == "16:00"

    def test_no_events_returns_empty(self) -> None:
        result = interpret("Qual é o tempo?", _llm("[]"))
        assert result == []

    def test_absolute_time_preserved(self) -> None:
        payload = '[{"action": "block_calendar", "title": "Atendimento Sandra Mariotto", "duration_minutes": 60, "start_time": "16:00"}]'
        llm = _llm(payload)
        result = interpret("às 16:00 atendo a professora Sandra Mariotto por uma hora", llm, now=_NOW)
        assert len(result) == 1
        assert result[0].start_time == "16:00"
        call_args = llm.complete.call_args[0][0]
        assert "[now: 13:15]" in call_args

    def test_invalid_json_returns_empty(self) -> None:
        result = interpret("qualquer coisa", _llm("not json"))
        assert result == []

    def test_strips_markdown_fences(self) -> None:
        payload = '```json\n[{"action": "block_calendar", "title": "Reunião", "duration_minutes": 60, "start_time": "10:00"}]\n```'
        result = interpret("reunião de 1 hora", _llm(payload), now=datetime(2024, 1, 15, 10, 0))
        assert len(result) == 1
        assert result[0].action == "block_calendar"

    def test_duration_clamped_to_minimum(self) -> None:
        payload = '[{"action": "block_calendar", "title": "Algo", "duration_minutes": 0, "start_time": "10:00"}]'
        result = interpret("algo rápido", _llm(payload), now=datetime(2024, 1, 15, 10, 0))
        assert result[0].duration_minutes == 1

    def test_llm_exception_returns_empty(self) -> None:
        llm = MagicMock()
        llm.complete.side_effect = Exception("network error")
        result = interpret("reunião de 1 hora", llm)
        assert result == []

    def test_skips_non_blocking_items_in_array(self) -> None:
        payload = '[{"action": "none"}, {"action": "block_calendar", "title": "Reunião", "duration_minutes": 30, "start_time": "14:00"}]'
        result = interpret("algo", _llm(payload), now=_NOW)
        assert len(result) == 1
        assert result[0].title == "Reunião"
