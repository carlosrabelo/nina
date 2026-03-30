# tests/test_schedule_parser.py
"""Tests for the structured schedule command parser."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from nina.skills.calendar.schedule_parser import parse

_TZ = ZoneInfo("America/Cuiaba")
_NOW = datetime(2024, 3, 28, 10, 0, 0, tzinfo=_TZ)  # Thursday 10:00


class TestScheduleParser:
    # ── time only (= today) ───────────────────────────────────────────────────

    def test_time_only_default_duration(self) -> None:
        r = parse("16:00 Reunião com Sandra", _NOW)
        assert r is not None
        assert r.start.hour == 16
        assert r.start.minute == 0
        assert r.start.date() == _NOW.date()
        assert r.duration_minutes == 60
        assert r.title == "Reunião com Sandra"

    def test_time_with_duration_hours(self) -> None:
        r = parse("14:30 Consultoria 2h", _NOW)
        assert r is not None
        assert r.start.hour == 14
        assert r.duration_minutes == 120
        assert r.title == "Consultoria"

    def test_time_with_duration_minutes(self) -> None:
        r = parse("09:00 Stand-up 30min", _NOW)
        assert r is not None
        assert r.duration_minutes == 30

    def test_time_with_duration_mixed(self) -> None:
        r = parse("10:00 Workshop 1h30", _NOW)
        assert r is not None
        assert r.duration_minutes == 90

    def test_time_with_duration_mixed_min_suffix(self) -> None:
        r = parse("10:00 Workshop 1h30min", _NOW)
        assert r is not None
        assert r.duration_minutes == 90

    # ── date keywords ─────────────────────────────────────────────────────────

    def test_today_keyword(self) -> None:
        r = parse("today 16:00 Reunião 1h", _NOW)
        assert r is not None
        assert r.start.date() == _NOW.date()
        assert r.start.hour == 16

    def test_hoje_keyword(self) -> None:
        r = parse("hoje 16:00 Reunião 1h", _NOW)
        assert r is not None
        assert r.start.date() == _NOW.date()

    def test_tomorrow_keyword(self) -> None:
        from datetime import timedelta
        r = parse("tomorrow 09:00 Consulta médica", _NOW)
        assert r is not None
        assert r.start.date() == _NOW.date() + timedelta(days=1)
        assert r.start.hour == 9

    def test_amanha_keyword(self) -> None:
        from datetime import timedelta
        r = parse("amanhã 09:00 Consulta médica", _NOW)
        assert r is not None
        assert r.start.date() == _NOW.date() + timedelta(days=1)

    # ── DD/MM date ────────────────────────────────────────────────────────────

    def test_ddmm_date(self) -> None:
        r = parse("29/03 14:00 Treinamento 2h", _NOW)
        assert r is not None
        assert r.start.month == 3
        assert r.start.day == 29
        assert r.start.year == 2024
        assert r.duration_minutes == 120

    def test_ddmmyyyy_date(self) -> None:
        r = parse("15/04/2024 10:00 Reunião anual", _NOW)
        assert r is not None
        assert r.start.month == 4
        assert r.start.day == 15
        assert r.start.year == 2024

    def test_ddmmyy_date_short_year(self) -> None:
        r = parse("15/04/25 10:00 Evento", _NOW)
        assert r is not None
        assert r.start.year == 2025

    # ── title edge cases ──────────────────────────────────────────────────────

    def test_multiword_title(self) -> None:
        r = parse("16:00 Atendimento Professora Vera Lucia 1h", _NOW)
        assert r is not None
        assert r.title == "Atendimento Professora Vera Lucia"
        assert r.duration_minutes == 60

    def test_title_only_no_duration(self) -> None:
        r = parse("16:00 Reunião", _NOW)
        assert r is not None
        assert r.title == "Reunião"
        assert r.duration_minutes == 60

    # ── timezone preserved ────────────────────────────────────────────────────

    def test_timezone_preserved(self) -> None:
        r = parse("16:00 Reunião", _NOW)
        assert r is not None
        assert r.start.tzinfo == _TZ

    # ── invalid inputs return None ────────────────────────────────────────────

    def test_empty_string(self) -> None:
        assert parse("", _NOW) is None

    def test_no_time(self) -> None:
        assert parse("Reunião sem horário", _NOW) is None

    def test_no_title(self) -> None:
        assert parse("16:00", _NOW) is None

    def test_no_title_with_duration_only(self) -> None:
        assert parse("16:00 1h", _NOW) is None

    def test_invalid_time(self) -> None:
        assert parse("25:00 Reunião", _NOW) is None

    def test_invalid_date(self) -> None:
        assert parse("32/13 16:00 Reunião", _NOW) is None
