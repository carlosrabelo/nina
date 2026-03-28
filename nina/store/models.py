# nina/store/models.py
"""Dataclasses for all persisted records."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


MemoStatus = Literal["open", "done", "dismissed"]
ActionStatus = Literal["open", "closed", "dismissed"]
ActionType = Literal["reply_needed", "follow_up", "reminder"]
EmailStatus = Literal["new", "seen", "actioned"]


@dataclass
class Memo:
    text: str
    source: Literal["text", "voice"] = "text"
    status: MemoStatus = "open"
    due_date: str | None = None          # ISO date string: 2026-03-28
    linked_event_id: str | None = None
    obsidian_path: str | None = None
    id: str = ""                         # assigned on insert (UUID)
    created_at: str = ""                 # ISO datetime, assigned on insert


@dataclass
class Action:
    type: ActionType
    source_type: str                     # "memo" | "email" | "event"
    source_id: str
    due_date: str | None = None
    status: ActionStatus = "open"
    id: str = ""
    created_at: str = ""


@dataclass
class EmailRecord:
    message_id: str
    account: str
    thread_id: str
    sender: str
    subject: str
    date: str                            # ISO datetime
    status: EmailStatus = "new"
    follow_up_due: str | None = None
    first_seen_at: str = ""


@dataclass
class EventRecord:
    event_id: str
    calendar_id: str
    account: str
    title: str
    start_at: str                        # ISO datetime
    end_at: str                          # ISO datetime
    briefing_done: bool = False
    first_seen_at: str = ""
