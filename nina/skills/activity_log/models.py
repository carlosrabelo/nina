"""Activity log models — intent and result types for past event logging."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class ActivityIntent:
    """Parsed activity logging intent from user text."""

    action: str                    # "log" | "query" | "summary" | "none"
    title: str = ""                # Activity description
    start: datetime | None = None  # Exact start time (if provided)
    end: datetime | None = None    # Exact end time (if provided)
    duration_minutes: int = 0      # Duration (if no exact end)
    target_date: date | None = None  # Date of activity (default: today)
    query_date: date | None = None   # For queries: which date/week
    query_type: str = ""           # "day" | "week" | "keyword"
    query_keyword: str = ""        # For keyword searches


@dataclass
class ActivityResult:
    """Result of executing an activity log intent."""

    success: bool = False
    title: str = ""
    start: datetime | None = None
    end: datetime | None = None
    link: str = ""                 # Google Calendar event URL
    account: str = ""
    message: str = ""              # Human-readable result message


@dataclass
class ActivityEntry:
    """A past activity entry returned from queries."""

    title: str
    start: datetime
    end: datetime
    account: str = ""
    calendar: str = ""
    link: str = ""
    description: str = ""


@dataclass
class ActivitySummary:
    """Aggregated summary of activities in a period."""

    period_label: str              # "Segunda 11/04" or "Semana de 07/04"
    total_minutes: int = 0
    entries: list[ActivityEntry] = field(default_factory=list)
    by_keyword: dict[str, int] = field(default_factory=dict)  # keyword → minutes
