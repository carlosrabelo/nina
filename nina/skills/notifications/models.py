"""Notification configuration and state models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NotificationConfig:
    reminder_minutes: int = 15   # how many minutes before event to send reminder
    watch_days: int = 7          # how many days ahead to watch for new/changed events


@dataclass
class KnownEvent:
    event_id: str
    account: str
    title: str
    start: str    # ISO datetime string
    end: str      # ISO datetime string
    updated: str  # ISO datetime string (last modification)


@dataclass
class QueuedNotification:
    id: str       # unique: event_id + type
    message: str  # formatted text to send


@dataclass
class NotificationState:
    config: NotificationConfig = field(default_factory=NotificationConfig)
    # event_id -> ISO date string (YYYY-MM-DD) when reminder was sent — for daily dedup
    reminders_sent: dict[str, str] = field(default_factory=dict)
    # account:event_id -> KnownEvent — for change detection
    known_events: dict[str, KnownEvent] = field(default_factory=dict)
    # notifications queued while DND or outside work hours
    queue: list[QueuedNotification] = field(default_factory=list)
    # whether notifications could be sent on the last job run — for flush-on-change
    last_can_notify: bool = True
