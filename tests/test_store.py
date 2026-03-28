# tests/test_store.py
"""Tests for the SQLite store — db, models, and memo repo."""

from pathlib import Path

import pytest

from nina.store.db import open_db
from nina.store.models import Action, EmailRecord, EventRecord, Memo
from nina.store.repos import action as action_repo
from nina.store.repos import email as email_repo
from nina.store.repos import event as event_repo
from nina.store.repos import memo as memo_repo


@pytest.fixture()
def conn(tmp_path: Path):  # type: ignore[no-untyped-def]
    return open_db(tmp_path)


# ── db ────────────────────────────────────────────────────────────────────────


class TestOpenDb:
    def test_creates_file(self, tmp_path: Path) -> None:
        open_db(tmp_path)
        assert (tmp_path / "nina.db").exists()

    def test_idempotent_migrations(self, tmp_path: Path) -> None:
        # Running twice should not raise
        open_db(tmp_path)
        open_db(tmp_path)

    def test_all_tables_created(self, tmp_path: Path) -> None:
        conn = open_db(tmp_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"memos", "actions", "emails", "calendar_events"}.issubset(tables)


# ── memo repo ─────────────────────────────────────────────────────────────────


class TestMemoRepo:
    def test_add_assigns_id_and_created_at(self, conn) -> None:  # type: ignore[no-untyped-def]
        m = memo_repo.add(conn, Memo(text="Ligar para o João"))
        assert m.id != ""
        assert m.created_at != ""

    def test_get_returns_memo(self, conn) -> None:  # type: ignore[no-untyped-def]
        m = memo_repo.add(conn, Memo(text="Comprar pão"))
        fetched = memo_repo.get(conn, m.id)
        assert fetched is not None
        assert fetched.text == "Comprar pão"

    def test_get_missing_returns_none(self, conn) -> None:  # type: ignore[no-untyped-def]
        assert memo_repo.get(conn, "nonexistent") is None

    def test_list_open_returns_only_open(self, conn) -> None:  # type: ignore[no-untyped-def]
        m1 = memo_repo.add(conn, Memo(text="A"))
        m2 = memo_repo.add(conn, Memo(text="B"))
        memo_repo.done(conn, m2.id)
        open_memos = memo_repo.list_open(conn)
        ids = [m.id for m in open_memos]
        assert m1.id in ids
        assert m2.id not in ids

    def test_done_closes_memo(self, conn) -> None:  # type: ignore[no-untyped-def]
        m = memo_repo.add(conn, Memo(text="C"))
        assert memo_repo.done(conn, m.id) is True
        assert memo_repo.get(conn, m.id).status == "done"  # type: ignore[union-attr]

    def test_dismiss_closes_memo(self, conn) -> None:  # type: ignore[no-untyped-def]
        m = memo_repo.add(conn, Memo(text="D"))
        assert memo_repo.dismiss(conn, m.id) is True
        assert memo_repo.get(conn, m.id).status == "dismissed"  # type: ignore[union-attr]

    def test_done_on_missing_returns_false(self, conn) -> None:  # type: ignore[no-untyped-def]
        assert memo_repo.done(conn, "no-such-id") is False

    def test_list_all_returns_all_statuses(self, conn) -> None:  # type: ignore[no-untyped-def]
        m1 = memo_repo.add(conn, Memo(text="E"))
        m2 = memo_repo.add(conn, Memo(text="F"))
        memo_repo.done(conn, m2.id)
        all_memos = memo_repo.list_all(conn)
        assert len(all_memos) == 2

    def test_memo_with_due_date(self, conn) -> None:  # type: ignore[no-untyped-def]
        m = memo_repo.add(conn, Memo(text="G", due_date="2026-04-01"))
        fetched = memo_repo.get(conn, m.id)
        assert fetched is not None
        assert fetched.due_date == "2026-04-01"

    def test_memo_source_voice(self, conn) -> None:  # type: ignore[no-untyped-def]
        m = memo_repo.add(conn, Memo(text="transcrição", source="voice"))
        fetched = memo_repo.get(conn, m.id)
        assert fetched is not None
        assert fetched.source == "voice"


# ── action repo ───────────────────────────────────────────────────────────────


class TestActionRepo:
    def test_add_and_list_open(self, conn) -> None:  # type: ignore[no-untyped-def]
        action_repo.add(conn, Action(type="reminder", source_type="memo", source_id="x"))
        open_actions = action_repo.list_open(conn)
        assert len(open_actions) == 1
        assert open_actions[0].type == "reminder"

    def test_close_action(self, conn) -> None:  # type: ignore[no-untyped-def]
        a = action_repo.add(conn, Action(type="follow_up", source_type="email", source_id="e1"))
        assert action_repo.close(conn, a.id) is True
        assert action_repo.list_open(conn) == []

    def test_close_missing_returns_false(self, conn) -> None:  # type: ignore[no-untyped-def]
        assert action_repo.close(conn, "no-such") is False


# ── email repo ────────────────────────────────────────────────────────────────


class TestEmailRepo:
    def _make_record(self, message_id: str = "msg1") -> EmailRecord:
        return EmailRecord(
            message_id=message_id,
            account="me@gmail.com",
            thread_id="thread1",
            sender="someone@example.com",
            subject="Hello",
            date="2026-03-28T10:00:00+00:00",
        )

    def test_upsert_and_get(self, conn) -> None:  # type: ignore[no-untyped-def]
        email_repo.upsert(conn, self._make_record())
        rec = email_repo.get(conn, "msg1")
        assert rec is not None
        assert rec.subject == "Hello"

    def test_upsert_updates_status(self, conn) -> None:  # type: ignore[no-untyped-def]
        r = self._make_record()
        email_repo.upsert(conn, r)
        r.status = "seen"
        email_repo.upsert(conn, r)
        assert email_repo.get(conn, "msg1").status == "seen"  # type: ignore[union-attr]

    def test_list_by_status(self, conn) -> None:  # type: ignore[no-untyped-def]
        email_repo.upsert(conn, self._make_record("m1"))
        email_repo.upsert(conn, self._make_record("m2"))
        r = self._make_record("m2")
        r.status = "seen"
        email_repo.upsert(conn, r)
        new_emails = email_repo.list_by_status(conn, "new")
        assert len(new_emails) == 1
        assert new_emails[0].message_id == "m1"


# ── event repo ────────────────────────────────────────────────────────────────


class TestEventRepo:
    def _make_record(self, event_id: str = "evt1") -> EventRecord:
        return EventRecord(
            event_id=event_id,
            calendar_id="primary",
            account="me@gmail.com",
            title="Reunião",
            start_at="2026-03-28T10:00:00+00:00",
            end_at="2026-03-28T11:00:00+00:00",
        )

    def test_upsert_and_get(self, conn) -> None:  # type: ignore[no-untyped-def]
        event_repo.upsert(conn, self._make_record())
        rec = event_repo.get(conn, "evt1", "me@gmail.com")
        assert rec is not None
        assert rec.title == "Reunião"

    def test_upsert_updates_title(self, conn) -> None:  # type: ignore[no-untyped-def]
        event_repo.upsert(conn, self._make_record())
        r = self._make_record()
        r.title = "Reunião atualizada"
        event_repo.upsert(conn, r)
        rec = event_repo.get(conn, "evt1", "me@gmail.com")
        assert rec is not None
        assert rec.title == "Reunião atualizada"

    def test_list_pending_briefing(self, conn) -> None:  # type: ignore[no-untyped-def]
        event_repo.upsert(conn, self._make_record("e1"))
        r2 = self._make_record("e2")
        r2.briefing_done = True
        event_repo.upsert(conn, r2)
        pending = event_repo.list_pending_briefing(conn)
        assert len(pending) == 1
        assert pending[0].event_id == "e1"
