# tests/test_memo_interpreter.py
"""Tests for the memo intent interpreter (Layer 1 + Layer 2)."""

from unittest.mock import MagicMock

from nina.skills.memo.interpreter import MemoIntent, interpret, try_action


class TestTryAction:
    def test_list_pt(self) -> None:
        result = try_action("quais os memos que eu tenho?", "pt")
        assert result is not None
        assert result.action == "list"
        assert result.subject == ""

    def test_list_en(self) -> None:
        result = try_action("show my memos", "en")
        assert result is not None
        assert result.action == "list"

    def test_list_ver_pt(self) -> None:
        result = try_action("ver meus memos", "pt")
        assert result is not None
        assert result.action == "list"

    def test_pt_word_ignored_in_en(self) -> None:
        # "quais" is PT — should not match when lang=en
        assert try_action("quais meus memos", "en") is None

    def test_en_word_ignored_in_pt(self) -> None:
        # "show" is EN — should not match when lang=pt
        assert try_action("show my memos", "pt") is None

    def test_close_pt(self) -> None:
        result = try_action('feche o memo "hd no servidor"', "pt")
        assert result is not None
        assert result.action == "close"
        assert result.subject == "hd no servidor"

    def test_close_pt_single_quotes(self) -> None:
        result = try_action("fechar memo 'comprar pão'", "pt")
        assert result is not None
        assert result.action == "close"
        assert result.subject == "comprar pão"

    def test_close_pt_no_quotes(self) -> None:
        result = try_action("feche o memo instalar hd", "pt")
        assert result is not None
        assert result.action == "close"
        assert "instalar" in result.subject

    def test_close_en(self) -> None:
        result = try_action('close memo "buy bread"', "en")
        assert result is not None
        assert result.action == "close"
        assert result.subject == "buy bread"

    def test_dismiss_pt(self) -> None:
        result = try_action('descarte o memo "reunião chata"', "pt")
        assert result is not None
        assert result.action == "dismiss"
        assert result.subject == "reunião chata"

    def test_no_memo_keyword_returns_none(self) -> None:
        assert try_action("bloqueia 15h para reunião", "pt") is None

    def test_no_action_word_returns_none(self) -> None:
        assert try_action("memo comprar pão", "pt") is None

    def test_empty_subject_returns_none(self) -> None:
        assert try_action('feche o memo ""', "pt") is None


class TestHasReminderContext:
    def test_me_lembre_pt(self) -> None:
        from nina.skills.memo.interpreter import has_reminder_context
        assert has_reminder_context("me lembre na segunda às 10h", "pt")

    def test_me_avisa_pt(self) -> None:
        from nina.skills.memo.interpreter import has_reminder_context
        assert has_reminder_context("me avisa amanhã de manhã", "pt")

    def test_remind_me_en(self) -> None:
        from nina.skills.memo.interpreter import has_reminder_context
        assert has_reminder_context("remind me on monday at 10am", "en")

    def test_no_reminder_keyword(self) -> None:
        from nina.skills.memo.interpreter import has_reminder_context
        assert not has_reminder_context("feche o memo compras", "pt")
        assert not has_reminder_context("bloqueia 15h para reunião", "pt")


class TestInterpret:
    def test_llm_close_intent(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = '{"action": "close", "subject": "comprar pão"}'
        intent = interpret("pode fechar aquele memo de compras?", llm)
        assert intent.action == "close"
        assert intent.subject == "comprar pão"

    def test_llm_dismiss_intent(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = '{"action": "dismiss", "subject": "reunião"}'
        intent = interpret("esquece o memo da reunião", llm)
        assert intent.action == "dismiss"

    def test_llm_list_intent(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = '{"action": "list", "subject": "", "due_date": null}'
        intent = interpret("pode me mostrar os memos?", llm)
        assert intent.action == "list"

    def test_llm_remind_intent(self) -> None:
        from datetime import datetime
        llm = MagicMock()
        llm.complete.return_value = '{"action": "remind", "subject": "formatar máquina Rafael", "due_date": "2026-03-30 10:00"}'
        now = datetime(2026, 3, 28, 14, 0)
        intent = interpret("me lembre na segunda às 10h que preciso formatar a máquina do Rafael", llm, lang="pt", now=now)
        assert intent.action == "remind"
        assert intent.due_date == "2026-03-30 10:00"
        assert "Rafael" in intent.subject

    def test_llm_remind_passes_now_in_prompt(self) -> None:
        from datetime import datetime
        llm = MagicMock()
        llm.complete.return_value = '{"action": "remind", "subject": "x", "due_date": "2026-03-30 10:00"}'
        now = datetime(2026, 3, 28, 14, 0)
        interpret("me lembre segunda às 10h de x", llm, lang="pt", now=now)
        call_text = llm.complete.call_args[0][0]
        assert "2026-03-28" in call_text  # now injected into prompt

    def test_llm_none_when_not_memo(self) -> None:
        llm = MagicMock()
        intent = interpret("bloqueia 15h para reunião", llm)
        assert intent.action == "none"
        llm.complete.assert_not_called()

    def test_llm_none_on_bad_json(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = "not json at all"
        intent = interpret("feche o memo teste", llm)
        assert intent.action == "none"

    def test_llm_none_on_exception(self) -> None:
        llm = MagicMock()
        llm.complete.side_effect = Exception("timeout")
        intent = interpret("feche o memo teste", llm)
        assert intent.action == "none"
