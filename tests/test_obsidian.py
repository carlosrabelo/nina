# tests/test_obsidian.py
"""Tests for the Obsidian writer and page renderers."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nina.obsidian import ensure_folders, vault_path, write_page
from nina.store.db import open_db
from nina.store.models import Memo
from nina.store.repos import memo as memo_repo


# ── writer ────────────────────────────────────────────────────────────────────


class TestVaultPath:
    def test_returns_none_when_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OBSIDIAN_VAULT_PATH", None)
            assert vault_path() is None

    def test_returns_path_when_set(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(tmp_path)}):
            assert vault_path() == tmp_path

    def test_expands_tilde(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(tmp_path)}):
            result = vault_path()
            assert result is not None
            assert "~" not in str(result)


class TestWritePage:
    def test_returns_none_when_vault_not_configured(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OBSIDIAN_VAULT_PATH", None)
            assert write_page("test.md", "content") is None

    def test_writes_file_to_vault(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(tmp_path)}):
            result = write_page("today.md", "# Today")
            assert result is not None
            assert result.exists()
            assert result.read_text() == "# Today"

    def test_writes_to_subfolder(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(tmp_path)}):
            result = write_page("note.md", "content", subfolder="daily")
            assert result is not None
            assert result.parent.name == "daily"
            assert result.exists()

    def test_creates_intermediate_dirs(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(tmp_path)}):
            result = write_page("note.md", "x", subfolder="a/b/c")
            assert result is not None
            assert result.exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(tmp_path)}):
            write_page("f.md", "v1")
            write_page("f.md", "v2")
            assert (tmp_path / "f.md").read_text() == "v2"

    def test_skips_write_when_content_unchanged(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(tmp_path)}):
            write_page("f.md", "same content")
            mtime_before = (tmp_path / "f.md").stat().st_mtime
            write_page("f.md", "same content")
            assert (tmp_path / "f.md").stat().st_mtime == mtime_before


class TestEnsureFolders:
    def test_creates_standard_folders(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(tmp_path)}):
            ensure_folders()
            for folder in ("daily", "digest", "captured", "permanent"):
                assert (tmp_path / folder).is_dir()

    def test_noop_when_vault_not_configured(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OBSIDIAN_VAULT_PATH", None)
            ensure_folders()  # should not raise


# ── open_page ─────────────────────────────────────────────────────────────────


class TestOpenPage:
    from nina.obsidian.open_page import render

    @pytest.fixture()
    def conn(self, tmp_path: Path):  # type: ignore[no-untyped-def]
        return open_db(tmp_path)

    def test_empty_memos_en(self, conn) -> None:  # type: ignore[no-untyped-def]
        from nina.obsidian.open_page import render
        content = render(conn, lang="en")
        assert "# Open" in content
        assert "No open memos" in content

    def test_empty_memos_pt(self, conn) -> None:  # type: ignore[no-untyped-def]
        from nina.obsidian.open_page import render
        content = render(conn, lang="pt")
        assert "# Abertos" in content
        assert "Nenhum memo aberto" in content

    def test_lists_open_memos(self, conn) -> None:  # type: ignore[no-untyped-def]
        from nina.obsidian.open_page import render
        memo_repo.add(conn, Memo(text="Call João"))
        memo_repo.add(conn, Memo(text="Buy bread", due_date="2026-04-01"))
        content = render(conn, lang="en")
        assert "Call João" in content
        assert "Buy bread" in content
        assert "2026-04-01" in content

    def test_closed_memos_not_listed(self, conn) -> None:  # type: ignore[no-untyped-def]
        from nina.obsidian.open_page import render
        m = memo_repo.add(conn, Memo(text="Done task"))
        memo_repo.done(conn, m.id)
        content = render(conn, lang="en")
        assert "Done task" not in content

    def test_voice_memo_has_tag(self, conn) -> None:  # type: ignore[no-untyped-def]
        from nina.obsidian.open_page import render
        memo_repo.add(conn, Memo(text="Voice note", source="voice"))
        content = render(conn, lang="en")
        assert "🎤" in content

    def test_short_id_in_content(self, conn) -> None:  # type: ignore[no-untyped-def]
        from nina.obsidian.open_page import render
        m = memo_repo.add(conn, Memo(text="Test"))
        content = render(conn, lang="en")
        assert m.id[:8] in content


# ── week_page ──────────────────────────────────────────────────────────────────


class TestWeekPage:
    @pytest.fixture()
    def conn(self, tmp_path: Path):  # type: ignore[no-untyped-def]
        return open_db(tmp_path)

    def _render(self, conn, lang: str = "en") -> str:
        from nina.obsidian.week_page import render
        return render(conn, accounts=[], tokens_dir=Path("/tmp"), lang=lang)

    def test_header_en(self, conn) -> None:  # type: ignore[no-untyped-def]
        content = self._render(conn, lang="en")
        assert "# Week —" in content

    def test_header_pt(self, conn) -> None:  # type: ignore[no-untyped-def]
        content = self._render(conn, lang="pt")
        assert "# Semana —" in content

    def test_seven_day_sections(self, conn) -> None:  # type: ignore[no-untyped-def]
        content = self._render(conn)
        # 7 day headers (## DayName, ...)
        assert content.count("## ") >= 8  # 7 days + due section

    def test_no_events_placeholder(self, conn) -> None:  # type: ignore[no-untyped-def]
        content = self._render(conn)
        assert "_No events._" in content

    def test_due_section_empty(self, conn) -> None:  # type: ignore[no-untyped-def]
        content = self._render(conn)
        assert "## Memos due this week" in content
        assert "_No memos due this week._" in content

    def test_due_memo_appears(self, conn) -> None:  # type: ignore[no-untyped-def]
        from zoneinfo import ZoneInfo
        future = (datetime.now(ZoneInfo("UTC")) + timedelta(days=3)).strftime("%Y-%m-%d")
        m = memo_repo.add(conn, Memo(text="Buy tickets", due_date=future))
        content = self._render(conn)
        assert "Buy tickets" in content
        assert future in content
        assert m.id[:8] in content

    def test_overdue_memo_flagged(self, conn) -> None:  # type: ignore[no-untyped-def]
        m = memo_repo.add(conn, Memo(text="Expired task", due_date="2020-01-01"))
        content = self._render(conn)
        assert "Expired task" in content
        assert "⚠️ Overdue" in content

    def test_closed_memo_not_in_due(self, conn) -> None:  # type: ignore[no-untyped-def]
        from zoneinfo import ZoneInfo
        future = (datetime.now(ZoneInfo("UTC")) + timedelta(days=2)).strftime("%Y-%m-%d")
        m = memo_repo.add(conn, Memo(text="Already done", due_date=future))
        memo_repo.done(conn, m.id)
        content = self._render(conn)
        assert "Already done" not in content

    def test_event_rendered(self, conn) -> None:  # type: ignore[no-untyped-def]
        from nina.google.calendar.client import Event
        from nina.obsidian.week_page import render
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("UTC")
        now = datetime.now(tz).replace(hour=10, minute=0, second=0, microsecond=0)
        ev = Event(
            id="evt1", account="a@b.com", title="Team standup",
            start=now, end=now.replace(hour=11),
            location="", calendar="primary",
        )
        mock_client = MagicMock()
        mock_client.list_in_window.return_value = [ev]

        with patch("nina.google.calendar.client.CalendarClient", return_value=mock_client):
            content = render(conn, accounts=["a@b.com"], tokens_dir=Path("/tmp"), lang="en")

        assert "Team standup" in content
        assert "10:00 → 11:00" in content
