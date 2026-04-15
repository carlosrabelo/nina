# tests/test_notification_interpreter.py
"""Tests for the notification intent interpreter (Layer 1 + Layer 2)."""

from unittest.mock import MagicMock

from nina.skills.notifications.interpreter import NotificationIntent, interpret, try_action


class TestTryAction:
    def test_get_pt(self) -> None:
        result = try_action("quais as notificações?", "pt")
        assert result is not None
        assert result.action == "get"

    def test_get_en(self) -> None:
        result = try_action("show notifications", "en")
        assert result is not None
        assert result.action == "get"

    def test_set_reminder_pt(self) -> None:
        result = try_action("muda o lembrete para 20 minutos", "pt")
        assert result is not None
        assert result.action == "set_reminder"
        assert result.minutes == 20

    def test_set_reminder_en(self) -> None:
        result = try_action("set reminder to 10 minutes", "en")
        assert result is not None
        assert result.action == "set_reminder"
        assert result.minutes == 10

    def test_set_days_pt(self) -> None:
        result = try_action("avisa com 5 dias de antecedência", "pt")
        assert result is not None
        assert result.action == "set_days"
        assert result.days == 5

    def test_no_keyword_returns_none(self) -> None:
        assert try_action("bloqueia 15h para reunião", "pt") is None
        assert try_action("quais meus memos?", "pt") is None


class TestInterpret:
    def test_llm_set_reminder(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = '{"action": "set_reminder", "minutes": 30, "days": null}'
        intent = interpret("quero ser avisado 30 minutos antes", llm)
        assert intent.action == "set_reminder"
        assert intent.minutes == 30

    def test_llm_none_when_no_keyword(self) -> None:
        llm = MagicMock()
        intent = interpret("bloqueia 15h para reunião", llm)
        assert intent.action == "none"
        llm.complete.assert_not_called()
