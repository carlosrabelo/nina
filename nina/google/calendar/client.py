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
    start: datetime
    end: datetime
    location: str
    calendar: str
    link: str = ""
    updated: str = ""   # ISO datetime of last modification

    @property
    def event_id(self) -> str:
        return self.id


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

    def list_in_window(
        self, start: datetime, end: datetime, calendar_id: str = "primary"
    ) -> list[Event]:
        """Return events that overlap with the [start, end] window."""
        try:
            result = (
                self._svc.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
        except HttpError as e:
            raise CalendarError(self.account, str(e)) from e
        return [self._parse(item) for item in result.get("items", [])]

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        calendar_id: str = "primary",
        description: str = "",
    ) -> Event:
        """Create a new event and return it."""
        body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start.isoformat()},
            "end":   {"dateTime": end.isoformat()},
        }
        try:
            raw = self._svc.events().insert(calendarId=calendar_id, body=body).execute()
        except HttpError as e:
            raise CalendarError(self.account, str(e)) from e
        return self._parse(raw)

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        """Parse a dateTime or date string from the Calendar API into a datetime."""
        if not value:
            return datetime.min.replace(tzinfo=timezone.utc)
        # dateTime format: 2024-03-28T16:00:00+00:00 or 2024-03-28T16:00:00Z
        # date format: 2024-03-28 (all-day events)
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        # All-day event: treat as midnight UTC
        from datetime import date
        d = date.fromisoformat(value)
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)

    def _parse(self, raw: dict) -> Event:  # type: ignore[type-arg]
        start_raw = raw.get("start", {})
        end_raw = raw.get("end", {})
        start_str = start_raw.get("dateTime", start_raw.get("date", ""))
        end_str = end_raw.get("dateTime", end_raw.get("date", ""))
        return Event(
            id=raw["id"],
            account=self.account,
            title=raw.get("summary", "(sem título)"),
            start=self._parse_dt(start_str),
            end=self._parse_dt(end_str),
            location=raw.get("location", ""),
            calendar=raw.get("organizer", {}).get("email", "primary"),
            link=raw.get("htmlLink", ""),
            updated=raw.get("updated", ""),
        )
