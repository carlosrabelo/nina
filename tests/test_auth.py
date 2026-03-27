# tests/test_auth.py
"""Tests for the OAuth credential management."""

import json
from pathlib import Path

import pytest

from nina.google.auth import _safe_name, discover_accounts, is_authenticated, revoke


class TestSafeName:
    def test_converts_at_sign(self) -> None:
        assert _safe_name("user@gmail.com") == "user_at_gmail_com"

    def test_replaces_dots(self) -> None:
        assert _safe_name("first.last@example.com") == "first_last_at_example_com"

    def test_plain_name_unchanged(self) -> None:
        assert _safe_name("nospecial") == "nospecial"


class TestIsAuthenticated:
    def test_returns_false_when_no_token(self, tmp_path: Path) -> None:
        assert is_authenticated("user@gmail.com", tmp_path) is False

    def test_returns_true_when_token_has_refresh(self, fake_token: Path) -> None:
        assert is_authenticated("user@gmail.com", fake_token) is True

    def test_returns_false_for_different_account(self, fake_token: Path) -> None:
        assert is_authenticated("other@gmail.com", fake_token) is False


class TestDiscoverAccounts:
    def test_returns_empty_when_no_tokens(self, tmp_path: Path) -> None:
        assert discover_accounts(tmp_path) == []

    def test_finds_accounts_with_nina_email(self, tmp_path: Path) -> None:
        for email in ["a@gmail.com", "b@gmail.com"]:
            token = tmp_path / f"{_safe_name(email)}.json"
            token.write_text(
                json.dumps({"refresh_token": "x", "_nina_email": email}),
                encoding="utf-8",
            )
        found = discover_accounts(tmp_path)
        assert sorted(found) == ["a@gmail.com", "b@gmail.com"]

    def test_ignores_tokens_without_nina_email(self, tmp_path: Path) -> None:
        (tmp_path / "old_token.json").write_text(
            '{"refresh_token": "x"}', encoding="utf-8"
        )
        assert discover_accounts(tmp_path) == []

    def test_skips_malformed_json(self, tmp_path: Path) -> None:
        (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
        assert discover_accounts(tmp_path) == []


class TestRevoke:
    def test_removes_existing_token(self, fake_token: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        revoke("user@gmail.com", fake_token)
        assert not (fake_token / "user_at_gmail_com.json").exists()

    def test_no_error_when_token_missing(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        revoke("nobody@gmail.com", tmp_path)
        out = capsys.readouterr().out
        assert "No token found" in out
