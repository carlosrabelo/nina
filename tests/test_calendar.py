# tests/test_calendar.py
"""Tests for the Google Calendar client."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from calendar_client import CalendarClient, Event


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
    with patch("calendar_client.get_credentials") as mock_creds, \
         patch("calendar_client.build") as mock_build:
        mock_creds.return_value = MagicMock()
        mock_build.return_value = MagicMock()
        return CalendarClient("user@gmail.com", tmp_path / "tokens")


class TestCalendarClientParse:
    def test_parse_basic_event(self, client: CalendarClient) -> None:
        raw = _make_raw_event()
        ev = client._parse(raw)
        assert ev.title == "Team sync"
        assert ev.account == "user@gmail.com"
        assert ev.start == "2026-03-27T10:00:00-03:00"
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
        assert ev.start == "2026-04-21"

    def test_parse_missing_title(self, client: CalendarClient) -> None:
        raw = {
            "id": "x",
            "start": {"date": "2026-04-21"},
            "end": {"date": "2026-04-22"},
        }
        ev = client._parse(raw)
        assert ev.title == "(sem título)"
