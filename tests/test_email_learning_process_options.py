"""Unit tests for Gmail query / cap helpers used by ``run_email_learning_process``."""

from nina.skills.email_learning.service import (
    _process_gmail_query,
    _process_max_messages,
)


def test_process_gmail_query_replaces_newer_than(monkeypatch) -> None:
    monkeypatch.setenv("NINA_EMAIL_SYNC_QUERY", "in:inbox newer_than:14d")
    q = _process_gmail_query(365)
    assert "newer_than:365d" in q
    assert "newer_than:14d" not in q


def test_process_gmail_query_appends_newer_than(monkeypatch) -> None:
    monkeypatch.setenv("NINA_EMAIL_SYNC_QUERY", "in:inbox")
    q = _process_gmail_query(90)
    assert "in:inbox" in q
    assert "newer_than:90d" in q


def test_process_gmail_query_none_uses_env(monkeypatch) -> None:
    monkeypatch.setenv("NINA_EMAIL_SYNC_QUERY", "label:x newer_than:7d")
    assert _process_gmail_query(None) == "label:x newer_than:7d"


def test_process_max_messages_cli_cap(monkeypatch) -> None:
    monkeypatch.setenv("NINA_EMAIL_SYNC_MAX_MESSAGES", "80")
    assert _process_max_messages(None) == 80
    assert _process_max_messages(2000) == 2000
    assert _process_max_messages(9000) == 5000
