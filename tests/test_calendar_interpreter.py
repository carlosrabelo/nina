# tests/test_calendar_interpreter.py
"""Tests for the calendar intent interpreter (Layer 1 + Layer 2)."""

from unittest.mock import MagicMock

from nina.skills.calendar.interpreter import CalendarIntent, interpret, try_action


class TestTryAction:
    def test_list_eventos_pt(self) -> None:
        result = try_action("quais meus eventos?", "pt")
        assert result is not None
        assert result.action == "list"

    def test_list_calendario_pt(self) -> None:
        result = try_action("mostre meu calendário", "pt")
        assert result is not None
        assert result.action == "list"

    def test_list_agenda_pt(self) -> None:
        result = try_action("ver minha agenda", "pt")
        assert result is not None
        assert result.action == "list"

    def test_list_calendar_en(self) -> None:
        result = try_action("show my calendar", "en")
        assert result is not None
        assert result.action == "list"

    def test_list_events_en(self) -> None:
        result = try_action("list upcoming events", "en")
        assert result is not None
        assert result.action == "list"

    def test_pt_keyword_ignored_in_en(self) -> None:
        # "eventos" is PT keyword — should not match when lang=en
        assert try_action("quais meus eventos?", "en") is None

    def test_en_keyword_ignored_in_pt(self) -> None:
        # "events" is EN keyword — should not match when lang=pt
        assert try_action("show my events", "pt") is None

    def test_no_memo_keyword_returns_none(self) -> None:
        assert try_action("quais meus memos?", "pt") is None

    def test_no_action_word_returns_none(self) -> None:
        assert try_action("criar evento reunião", "pt") is None


class TestInterpret:
    def test_llm_list_intent(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = '{"action": "list"}'
        intent = interpret("pode me mostrar os próximos eventos?", llm, "pt")
        assert intent.action == "list"

    def test_llm_none_when_no_keyword_pt(self) -> None:
        llm = MagicMock()
        intent = interpret("bloqueia 15h para reunião", llm, "pt")
        assert intent.action == "none"
        llm.complete.assert_not_called()

    def test_llm_none_on_bad_json(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = "not json"
        intent = interpret("liste meus eventos", llm, "pt")
        assert intent.action == "none"
