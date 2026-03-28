# tests/test_presence_interpreter.py
"""Tests for the LLM presence interpreter."""

from unittest.mock import MagicMock

from nina.presence.interpreter import PresenceIntent, interpret
from nina.presence.models import PresenceStatus


def _llm(response: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = response
    return llm


class TestInterpret:
    def test_set_office(self) -> None:
        llm = _llm('{"action": "set_presence", "status": "office", "note": ""}')
        result = interpret("Cheguei no trabalho", llm)
        assert result.action == "set_presence"
        assert result.status == PresenceStatus.OFFICE

    def test_set_home_with_note(self) -> None:
        llm = _llm('{"action": "set_presence", "status": "home", "note": "home office"}')
        result = interpret("Vou trabalhar de casa hoje", llm)
        assert result.status == PresenceStatus.HOME
        assert result.note == "home office"

    def test_set_dnd(self) -> None:
        llm = _llm('{"action": "set_presence", "status": "dnd", "note": "em reunião"}')
        result = interpret("Não me perturbe", llm)
        assert result.status == PresenceStatus.DND

    def test_set_out(self) -> None:
        llm = _llm('{"action": "set_presence", "status": "out", "note": ""}')
        result = interpret("Saindo para almoço", llm)
        assert result.status == PresenceStatus.OUT

    def test_action_none_returns_none_intent(self) -> None:
        llm = _llm('{"action": "none"}')
        result = interpret("Qual é o tempo?", llm)
        assert result.action == "none"
        assert result.status is None

    def test_invalid_json_returns_none(self) -> None:
        llm = _llm("not json at all")
        result = interpret("qualquer coisa", llm)
        assert result.action == "none"

    def test_unknown_status_returns_none(self) -> None:
        llm = _llm('{"action": "set_presence", "status": "flying", "note": ""}')
        result = interpret("qualquer coisa", llm)
        assert result.action == "none"

    def test_strips_markdown_fences(self) -> None:
        llm = _llm('```json\n{"action": "set_presence", "status": "home", "note": ""}\n```')
        result = interpret("cheguei em casa", llm)
        assert result.status == PresenceStatus.HOME

    def test_llm_exception_returns_none(self) -> None:
        llm = MagicMock()
        llm.complete.side_effect = Exception("network error")
        result = interpret("cheguei no trabalho", llm)
        assert result.action == "none"

    def test_set_dnd_training(self) -> None:
        llm = _llm('{"action": "set_presence", "status": "dnd", "note": "treinamento"}')
        result = interpret("estou num treinamento", llm)
        assert result.status == PresenceStatus.DND
        assert result.note == "treinamento"

    def test_set_dnd_course(self) -> None:
        llm = _llm('{"action": "set_presence", "status": "dnd", "note": "curso"}')
        result = interpret("estou num curso agora", llm)
        assert result.status == PresenceStatus.DND

    def test_set_dnd_presentation(self) -> None:
        llm = _llm('{"action": "set_presence", "status": "dnd", "note": "apresentação"}')
        result = interpret("em uma apresentação", llm)
        assert result.status == PresenceStatus.DND
