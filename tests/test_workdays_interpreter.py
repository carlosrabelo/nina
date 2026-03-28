# tests/test_workdays_interpreter.py
"""Tests for the LLM workdays interpreter."""

from datetime import time
from unittest.mock import MagicMock

from nina.workdays.interpreter import ScheduleChange, ScheduleIntent, apply, interpret
from nina.workdays.models import default_schedule


def _llm(response: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = response
    return llm


class TestInterpret:
    def test_full_week_schedule(self) -> None:
        payload = """{
            "action": "update_schedule",
            "changes": [
                {"day": 0, "active": true, "start": "09:00", "end": "18:00"},
                {"day": 1, "active": true, "start": "09:00", "end": "18:00"},
                {"day": 2, "active": true, "start": "09:00", "end": "18:00"},
                {"day": 3, "active": true, "start": "09:00", "end": "18:00"},
                {"day": 4, "active": true, "start": "09:00", "end": "18:00"}
            ]}"""
        result = interpret("Trabalho de segunda a sexta das 9 às 18", _llm(payload))
        assert result.action == "update_schedule"
        assert len(result.changes) == 5
        assert result.changes[0].start == time(9, 0)
        assert result.changes[0].end == time(18, 0)

    def test_single_day_end_change(self) -> None:
        payload = '{"action": "update_schedule", "changes": [{"day": 4, "active": true, "start": null, "end": "17:00"}]}'
        result = interpret("Sexta-feira eu saio às 17", _llm(payload))
        assert len(result.changes) == 1
        assert result.changes[0].day == 4
        assert result.changes[0].end == time(17, 0)
        assert result.changes[0].start is None

    def test_deactivate_day(self) -> None:
        payload = '{"action": "update_schedule", "changes": [{"day": 2, "active": false, "start": null, "end": null}]}'
        result = interpret("Não trabalho às quartas", _llm(payload))
        assert result.changes[0].active is False

    def test_action_none(self) -> None:
        result = interpret("Qual é o tempo?", _llm('{"action": "none"}'))
        assert result.action == "none"
        assert result.changes == []

    def test_invalid_json_returns_none(self) -> None:
        result = interpret("qualquer coisa", _llm("not json"))
        assert result.action == "none"

    def test_strips_markdown_fences(self) -> None:
        payload = '```json\n{"action": "update_schedule", "changes": [{"day": 0, "active": true, "start": "08:00", "end": "17:00"}]}\n```'
        result = interpret("começo às 8", _llm(payload))
        assert result.action == "update_schedule"

    def test_invalid_day_skipped(self) -> None:
        payload = '{"action": "update_schedule", "changes": [{"day": 9, "active": true, "start": "09:00", "end": "18:00"}]}'
        result = interpret("qualquer coisa", _llm(payload))
        assert result.action == "none"


class TestApply:
    def test_updates_start_and_end(self) -> None:
        schedule = default_schedule()
        intent = ScheduleIntent(action="update_schedule", changes=[
            ScheduleChange(day=0, active=True, start=time(8, 30), end=time(17, 0)),
        ])
        apply(intent, schedule)
        mon = next(d for d in schedule.days if d.day == 0)
        assert mon.start == time(8, 30)
        assert mon.end == time(17, 0)

    def test_deactivates_day(self) -> None:
        schedule = default_schedule()
        intent = ScheduleIntent(action="update_schedule", changes=[
            ScheduleChange(day=2, active=False, start=None, end=None),
        ])
        apply(intent, schedule)
        wed = next(d for d in schedule.days if d.day == 2)
        assert wed.active is False
        assert wed.start is None
        assert wed.end is None

    def test_null_start_preserves_existing(self) -> None:
        schedule = default_schedule()
        intent = ScheduleIntent(action="update_schedule", changes=[
            ScheduleChange(day=4, active=True, start=None, end=time(17, 0)),
        ])
        apply(intent, schedule)
        fri = next(d for d in schedule.days if d.day == 4)
        assert fri.start == time(9, 0)   # preserved
        assert fri.end == time(17, 0)    # updated
