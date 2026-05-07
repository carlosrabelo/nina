"""Tests for the local NLP parser and local intent router."""

from __future__ import annotations

from datetime import UTC, date, datetime

from nina.core.intent.local_router import (
    route as local_route,
)
from nina.core.intent.local_router import (
    try_blocking,
    try_calendar,
    try_memo,
    try_notifications,
    try_presence,
)
from nina.core.nlp import (
    DateEntity,
    DurationEntity,
    TimeEntity,
    parse_date_relative,
    parse_duration,
    parse_time,
)

NOW = datetime(2026, 4, 11, 10, 0, tzinfo=UTC)  # Saturday

# ── NLP: Time parsing ───────────────────────────────────────────────────────


class TestParseTime:
    def test_hour_h(self) -> None:
        ent = parse_time("às 14h")
        assert ent == TimeEntity(hour=14, minute=0)

    def test_hour_colon(self) -> None:
        ent = parse_time("at 9:30")
        assert ent == TimeEntity(hour=9, minute=30)

    def test_hour_h30(self) -> None:
        ent = parse_time("14h30")
        assert ent == TimeEntity(hour=14, minute=30)

    def test_no_time(self) -> None:
        assert parse_time("hello world") is None

    def test_invalid_hour(self) -> None:
        assert parse_time("25h") is None


# ── NLP: Duration parsing ──────────────────────────────────────────────────


class TestParseDuration:
    def test_por_1_hora(self) -> None:
        ent = parse_duration("por 1 hora")
        assert ent == DurationEntity(minutes=60)

    def test_30min(self) -> None:
        ent = parse_duration("30min")
        assert ent == DurationEntity(minutes=30)

    def test_1h30(self) -> None:
        ent = parse_duration("1h30")
        assert ent == DurationEntity(minutes=90)

    def test_por_2_horas(self) -> None:
        ent = parse_duration("por 2 horas")
        assert ent == DurationEntity(minutes=120)

    def test_no_duration(self) -> None:
        assert parse_duration("hello world") is None


# ── NLP: Date relative ─────────────────────────────────────────────────────


class TestParseDateRelative:
    def test_hoje(self) -> None:
        ent = parse_date_relative("hoje", NOW)
        assert ent == DateEntity(date=date(2026, 4, 11))

    def test_amanha(self) -> None:
        ent = parse_date_relative("amanhã", NOW)
        assert ent == DateEntity(date=date(2026, 4, 12))

    def test_tomorrow_en(self) -> None:
        ent = parse_date_relative("tomorrow", NOW)
        assert ent == DateEntity(date=date(2026, 4, 12))

    def test_next_weekday_pt(self) -> None:
        # NOW is Saturday 2026-04-11. Next Monday = 2026-04-13.
        ent = parse_date_relative("próxima segunda", NOW)
        assert ent == DateEntity(date=date(2026, 4, 13))

    def test_next_monday_en(self) -> None:
        ent = parse_date_relative("next monday", NOW)
        assert ent == DateEntity(date=date(2026, 4, 13))

    def test_numeric_date(self) -> None:
        ent = parse_date_relative("29/03", NOW)
        assert ent == DateEntity(date=date(2026, 3, 29))

    def test_no_date(self) -> None:
        assert parse_date_relative("hello world", NOW) is None


# ── Local Router: Presence ──────────────────────────────────────────────────


class TestLocalPresence:
    def test_cheguei_trabalho(self) -> None:
        r = try_presence("cheguei no trabalho", "pt")
        assert r is not None
        assert r.entities["status"] == "work"

    def test_estou_em_casa(self) -> None:
        r = try_presence("estou em casa", "pt")
        assert r is not None
        assert r.entities["status"] == "home"

    def test_saindo_almoco(self) -> None:
        r = try_presence("saindo para o almoço", "pt")
        assert r is not None
        assert r.entities["status"] == "out"

    def test_em_reuniao(self) -> None:
        r = try_presence("em reunião com Sandra", "pt")
        assert r is not None
        assert r.entities["status"] == "dnd"

    def test_at_office_en(self) -> None:
        r = try_presence("just got to the office", "en")
        assert r is not None
        assert r.entities["status"] == "work"

    def test_no_match(self) -> None:
        assert try_presence("qual é o tempo?", "pt") is None


# ── Local Router: Memo ─────────────────────────────────────────────────────


class TestLocalMemo:
    def test_memo_create(self) -> None:
        r = try_memo("memo comprar pão", "pt")
        assert r is not None
        assert r.action == "create"
        assert r.entities["subject"] == "comprar pão"

    def test_memo_list(self) -> None:
        r = try_memo("quais meus memos", "pt")
        assert r is not None
        assert r.action == "list"

    def test_reminder_with_date(self, now: datetime = NOW) -> None:
        r = try_memo("me lembra de ligar amanhã às 10h", "pt", now)
        assert r is not None
        assert r.action == "remind"
        assert "ligar" in r.entities["subject"]
        assert r.entities.get("due_date", "").startswith("2026-04-12")

    def test_reminder_en(self, now: datetime = NOW) -> None:
        r = try_memo("remind me to call John tomorrow at 9:00", "en", now)
        assert r is not None
        assert r.action == "remind"
        assert "John" in r.entities["subject"]

    def test_no_match(self) -> None:
        assert try_memo("qual é o tempo?", "pt") is None


# ── Local Router: Calendar ─────────────────────────────────────────────────


class TestLocalCalendar:
    def test_meus_eventos(self) -> None:
        r = try_calendar("quais meus eventos", "pt")
        assert r is not None
        assert r.action == "list"

    def test_minha_agenda(self) -> None:
        r = try_calendar("o que tenho hoje", "pt")
        assert r is not None
        assert r.action == "list"

    def test_my_events_en(self) -> None:
        r = try_calendar("my events today", "en")
        assert r is not None
        assert r.action == "list"

    def test_no_match(self) -> None:
        assert try_calendar("estou em casa", "pt") is None


# ── Local Router: Notifications ────────────────────────────────────────────


class TestLocalNotifications:
    def test_set_reminder_pt(self) -> None:
        r = try_notifications("me avisa 30 minutos antes", "pt")
        assert r is not None
        assert r.action == "set_reminder"
        assert r.entities["minutes"] == 30

    def test_set_days_pt(self) -> None:
        r = try_notifications("notificação com 2 dias de antecedência", "pt")
        assert r is not None
        assert r.action == "set_days"
        assert r.entities["days"] == 2

    def test_get(self) -> None:
        r = try_notifications("quais minhas notificações", "pt")
        assert r is not None
        assert r.action == "get"

    def test_no_match(self) -> None:
        assert try_notifications("estou em casa", "pt") is None


# ── Local Router: Blocking ─────────────────────────────────────────────────


class TestLocalBlocking:
    def test_with_time(self) -> None:
        r = try_blocking("agenda dentista amanhã às 9h", "pt")
        assert r is not None
        assert r.action == "create"
        assert "dentista" in r.entities["title"].lower()

    def test_with_duration(self) -> None:
        r = try_blocking("estou em reunião por 1 hora", "pt")
        assert r is not None
        assert r.action == "create"

    def test_no_time_no_match(self) -> None:
        # "em reunião" without time → presence, not blocking
        assert try_blocking("em reunião com Sandra", "pt") is None

    def test_schedule_en(self) -> None:
        r = try_blocking("schedule team meeting at 14:00 for 1 hour", "en")
        assert r is not None
        assert r.action == "create"


# ── Local Router: Orchestrator ─────────────────────────────────────────────


class TestLocalRoute:
    def test_presence_priority(self) -> None:
        r = local_route("estou em casa", "pt")
        assert r is not None
        assert r.domain == "presence"

    def test_memo(self) -> None:
        r = local_route("memo comprar leite", "pt")
        assert r is not None
        assert r.domain == "memo"
        assert r.action == "create"

    def test_calendar(self) -> None:
        r = local_route("quais meus eventos", "pt")
        assert r is not None
        assert r.domain == "calendar"

    def test_notifications(self) -> None:
        r = local_route("avisa 30 minutos antes dos eventos", "pt")
        assert r is not None
        assert r.domain == "notifications"

    def test_no_match_returns_none(self) -> None:
        assert local_route("qual é o tempo?", "pt") is None
        assert local_route("conta uma piada", "pt") is None
        assert local_route("what is machine learning", "en") is None

    def test_workdays_not_matched_locally(self) -> None:
        # workdays requires LLM — should fall through
        assert local_route("trabalho de segunda a sexta", "pt") is None

    def test_profile_not_matched_locally(self) -> None:
        # "no escritório" alone is correctly matched as presence (work)
        # Profile intent requires account mapping which has no local pattern
        r = local_route("no escritório usar work@co.com", "pt")
        # This may be presence (local) or None — profile needs LLM
        assert r is None or r.domain == "presence"
