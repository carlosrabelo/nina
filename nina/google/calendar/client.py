# nina/google/calendar/client.py
"""Google Calendar client supporting multiple accounts."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from nina.google.auth import get_credentials
from nina.errors import CalendarError


@dataclass
class Calendar:
    """A Google Calendar entry from the user's calendar list."""

    id: str
    name: str
    primary: bool
    access_role: str  # owner, writer, reader, freeBusyReader


@dataclass
class Event:
    """A Calendar event with the most relevant fields."""

    id: str
    account: str
    title: str
    start: str
    end: str
    location: str
    calendar: str


class CalendarClient:
    """Google Calendar client for a single account."""

    def __init__(self, account: str, tokens_dir: Path) -> None:
        self.account = account
        creds = get_credentials(account, tokens_dir)
        self._svc = build("calendar", "v3", credentials=creds)

    def list_calendars(self) -> list[Calendar]:
        """Return all calendars in the account's calendar list."""
        try:
            result = self._svc.calendarList().list().execute()
        except HttpError as e:
            raise CalendarError(self.account, str(e)) from e

        return [
            Calendar(
                id=item["id"],
                name=item.get("summary", "(sem nome)"),
                primary=item.get("primary", False),
                access_role=item.get("accessRole", ""),
            )
            for item in result.get("items", [])
        ]

    def list_upcoming(
        self, max_results: int = 10, calendar_id: str = "primary"
    ) -> list[Event]:
        """Return up to *max_results* upcoming events from *calendar_id*."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            result = (
                self._svc.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
        except HttpError as e:
            raise CalendarError(self.account, str(e)) from e

        return [self._parse(item) for item in result.get("items", [])]

    def list_next_days(self, days: int = 3) -> list[Event]:
        """Return all events across every calendar within the next *days* days.

        Queries each calendar individually, deduplicates by event id, and
        returns the combined list sorted by start time.
        """
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days)).isoformat()

        try:
            calendars = self.list_calendars()
        except CalendarError:
            calendars = []

        seen: set[str] = set()
        events: list[Event] = []

        for cal in calendars:
            try:
                result = (
                    self._svc.events()
                    .list(
                        calendarId=cal.id,
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )
            except HttpError:
                continue

            for item in result.get("items", []):
                eid = item["id"]
                if eid not in seen:
                    seen.add(eid)
                    events.append(self._parse(item))

        events.sort(key=lambda e: e.start)
        return events

    def _parse(self, raw: dict) -> Event:  # type: ignore[type-arg]
        start = raw.get("start", {})
        end = raw.get("end", {})
        return Event(
            id=raw["id"],
            account=self.account,
            title=raw.get("summary", "(sem título)"),
            start=start.get("dateTime", start.get("date", "")),
            end=end.get("dateTime", end.get("date", "")),
            location=raw.get("location", ""),
            calendar=raw.get("organizer", {}).get("email", "primary"),
        )
