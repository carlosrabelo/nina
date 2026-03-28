# tests/test_notifications.py
"""Tests for the notifications models and store."""

import json
from pathlib import Path

import pytest

from nina.notifications.models import (
    KnownEvent,
    NotificationConfig,
    NotificationState,
    QueuedNotification,
)
from nina.notifications.store import load, save


class TestNotificationModels:
    def test_default_config(self) -> None:
        config = NotificationConfig()
        assert config.reminder_minutes == 15
        assert config.watch_days == 7

    def test_default_state(self) -> None:
        state = NotificationState()
        assert state.config.reminder_minutes == 15
        assert state.reminders_sent == {}
        assert state.known_events == {}
        assert state.queue == []
        assert state.last_can_notify is True


class TestNotificationStore:
    def test_load_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        state = load(tmp_path)
        assert state.config.reminder_minutes == 15
        assert state.config.watch_days == 7
        assert state.queue == []

    def test_save_and_reload(self, tmp_path: Path) -> None:
        state = NotificationState()
        state.config.reminder_minutes = 10
        state.config.watch_days = 14
        state.reminders_sent["ev1:2024-03-28"] = "2024-03-28"
        state.known_events["acc:ev1"] = KnownEvent(
            event_id="ev1", account="acc@test.com",
            title="Reunião", start="2024-03-28T10:00:00",
            end="2024-03-28T11:00:00", updated="2024-03-28T09:00:00",
        )
        state.queue.append(QueuedNotification(id="q1", message="test msg"))
        state.last_can_notify = False

        save(state, tmp_path)
        loaded = load(tmp_path)

        assert loaded.config.reminder_minutes == 10
        assert loaded.config.watch_days == 14
        assert loaded.reminders_sent["ev1:2024-03-28"] == "2024-03-28"
        assert "acc:ev1" in loaded.known_events
        assert loaded.known_events["acc:ev1"].title == "Reunião"
        assert len(loaded.queue) == 1
        assert loaded.queue[0].message == "test msg"
        assert loaded.last_can_notify is False

    def test_load_corrupted_file_returns_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "notifications.json").write_text("not json")
        state = load(tmp_path)
        assert state.config.reminder_minutes == 15

    def test_queue_accumulates(self, tmp_path: Path) -> None:
        state = NotificationState()
        state.queue.append(QueuedNotification(id="a", message="msg A"))
        state.queue.append(QueuedNotification(id="b", message="msg B"))
        save(state, tmp_path)
        loaded = load(tmp_path)
        assert len(loaded.queue) == 2
        assert loaded.queue[0].id == "a"
        assert loaded.queue[1].id == "b"

    def test_known_event_key_format(self, tmp_path: Path) -> None:
        state = NotificationState()
        state.known_events["work@co.com:abc123"] = KnownEvent(
            event_id="abc123", account="work@co.com",
            title="Meeting", start="2024-03-28T14:00:00+00:00",
            end="2024-03-28T15:00:00+00:00", updated="",
        )
        save(state, tmp_path)
        loaded = load(tmp_path)
        ev = loaded.known_events["work@co.com:abc123"]
        assert ev.event_id == "abc123"
        assert ev.account == "work@co.com"
