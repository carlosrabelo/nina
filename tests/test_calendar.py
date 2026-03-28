# tests/test_calendar.py
"""Tests for the Google Calendar client."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nina.google.calendar.client import CalendarClient, Event


def _make_raw_event(
    event_id: str = "evt1",
    title: str = "Team sync",
    start: str = "2026-03-27T10:00:00-03:00",
    end: str = "2026-03-27T11:00:00-03:00",
    location: str = "",
) -> dict:  # type: ignore[type-arg]
    raw: dict = {  # type: ignore[type-arg]
        "id": event_id,
        "summary": title,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "organizer": {"email": "primary"},
    }
    if location:
        raw["location"] = location
    return raw


@pytest.fixture()
def client(tmp_path: Path) -> CalendarClient:
    with patch("nina.google.calendar.client.get_credentials") as mock_creds, \
         patch("nina.google.calendar.client.build") as mock_build:
        mock_creds.return_value = MagicMock()
        mock_build.return_value = MagicMock()
        return CalendarClient("user@gmail.com", tmp_path / "tokens")


class TestCalendarClientParse:
    def test_parse_basic_event(self, client: CalendarClient) -> None:
        raw = _make_raw_event()
        ev = client._parse(raw)
        assert ev.title == "Team sync"
        assert ev.account == "user@gmail.com"
        assert ev.start == datetime(2026, 3, 27, 10, 0, tzinfo=timezone(timedelta(hours=-3)))
        assert ev.location == ""

    def test_parse_event_with_location(self, client: CalendarClient) -> None:
        raw = _make_raw_event(location="Sala 3")
        ev = client._parse(raw)
        assert ev.location == "Sala 3"

    def test_parse_all_day_event(self, client: CalendarClient) -> None:
        raw = {
            "id": "x",
            "summary": "Feriado",
            "start": {"date": "2026-04-21"},
            "end": {"date": "2026-04-22"},
            "organizer": {"email": "primary"},
        }
        ev = client._parse(raw)
        assert ev.start == datetime(2026, 4, 21, 0, 0, tzinfo=timezone.utc)

    def test_parse_missing_title(self, client: CalendarClient) -> None:
        raw = {
            "id": "x",
            "start": {"date": "2026-04-21"},
            "end": {"date": "2026-04-22"},
        }
        ev = client._parse(raw)
        assert ev.title == "(sem título)"


class TestListNextDays:
    def _setup_client(self, tmp_path: Path, calendars: list, events_by_cal: dict) -> CalendarClient:  # type: ignore[type-arg]
        with patch("nina.google.calendar.client.get_credentials") as mock_creds, \
             patch("nina.google.calendar.client.build") as mock_build:
            mock_creds.return_value = MagicMock()
            svc = MagicMock()
            mock_build.return_value = svc

            svc.calendarList().list().execute.return_value = {"items": calendars}

            def events_list(**kwargs):  # type: ignore[no-untyped-def]
                cal_id = kwargs.get("calendarId", "primary")
                mock = MagicMock()
                mock.execute.return_value = {"items": events_by_cal.get(cal_id, [])}
                return mock

            svc.events().list.side_effect = events_list

            return CalendarClient("user@gmail.com", tmp_path / "tokens")

    def test_returns_events_from_all_calendars(self, tmp_path: Path) -> None:
        calendars = [
            {"id": "primary", "summary": "Pessoal", "primary": True, "accessRole": "owner"},
            {"id": "work@cal", "summary": "Trabalho", "primary": False, "accessRole": "owner"},
        ]
        events_by_cal = {
            "primary": [_make_raw_event("e1", "Dentista")],
            "work@cal": [_make_raw_event("e2", "Reunião")],
        }
        client = self._setup_client(tmp_path, calendars, events_by_cal)
        events = client.list_next_days(days=3)
        titles = [e.title for e in events]
        assert "Dentista" in titles
        assert "Reunião" in titles

    def test_deduplicates_same_event_in_multiple_calendars(self, tmp_path: Path) -> None:
        calendars = [
            {"id": "cal1", "summary": "A", "primary": False, "accessRole": "owner"},
            {"id": "cal2", "summary": "B", "primary": False, "accessRole": "owner"},
        ]
        shared = _make_raw_event("same-id", "Evento compartilhado")
        events_by_cal = {"cal1": [shared], "cal2": [shared]}
        client = self._setup_client(tmp_path, calendars, events_by_cal)
        events = client.list_next_days(days=3)
        assert len(events) == 1

    def test_returns_empty_when_no_events(self, tmp_path: Path) -> None:
        calendars = [{"id": "primary", "summary": "P", "primary": True, "accessRole": "owner"}]
        client = self._setup_client(tmp_path, calendars, {})
        events = client.list_next_days(days=3)
        assert events == []

    def test_skips_calendar_on_http_error(self, tmp_path: Path) -> None:
        from googleapiclient.errors import HttpError
        calendars = [
            {"id": "ok", "summary": "OK", "primary": False, "accessRole": "owner"},
            {"id": "bad", "summary": "Bad", "primary": False, "accessRole": "owner"},
        ]
        with patch("nina.google.calendar.client.get_credentials"), \
             patch("nina.google.calendar.client.build") as mock_build:
            svc = MagicMock()
            mock_build.return_value = svc
            svc.calendarList().list().execute.return_value = {"items": calendars}

            def events_list(**kwargs):  # type: ignore[no-untyped-def]
                cal_id = kwargs.get("calendarId")
                if cal_id == "bad":
                    raise HttpError(MagicMock(status=403), b"forbidden")
                mock = MagicMock()
                mock.execute.return_value = {"items": [_make_raw_event("e1", "OK event")]}
                return mock

            svc.events().list.side_effect = events_list
            client = CalendarClient("user@gmail.com", tmp_path / "tokens")

        events = client.list_next_days(days=3)
        assert len(events) == 1
        assert events[0].title == "OK event"
