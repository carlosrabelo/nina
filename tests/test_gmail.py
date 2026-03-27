# tests/test_gmail.py
"""Tests for the Gmail multi-account client."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from errors import ConfigError
from gmail import GmailClient, GmailMultiClient, Message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw_message(
    msg_id: str = "abc123",
    subject: str = "Hello",
    sender: str = "friend@example.com",
    snippet: str = "Hey there",
    labels: list[str] | None = None,
) -> dict:  # type: ignore[type-arg]
    return {
        "id": msg_id,
        "snippet": snippet,
        "labelIds": labels if labels is not None else ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
            ]
        },
    }


# ---------------------------------------------------------------------------
# GmailClient._parse
# ---------------------------------------------------------------------------

class TestGmailClientParse:
    @pytest.fixture()
    def client(self, tmp_path: Path) -> GmailClient:
        with patch("gmail.get_credentials") as mock_creds, \
             patch("gmail.build") as mock_build:
            mock_creds.return_value = MagicMock()
            mock_build.return_value = MagicMock()
            return GmailClient("user@gmail.com", tmp_path / "tokens")

    def test_parse_unread_message(self, client: GmailClient) -> None:
        raw = _make_raw_message(labels=["INBOX", "UNREAD"])
        msg = client._parse(raw)
        assert msg.is_read is False
        assert msg.subject == "Hello"
        assert msg.sender == "friend@example.com"
        assert msg.account == "user@gmail.com"

    def test_parse_read_message(self, client: GmailClient) -> None:
        raw = _make_raw_message(labels=["INBOX"])
        msg = client._parse(raw)
        assert msg.is_read is True

    def test_parse_missing_subject(self, client: GmailClient) -> None:
        raw = {"id": "x", "snippet": "", "labelIds": [], "payload": {"headers": []}}
        msg = client._parse(raw)
        assert msg.subject == "(no subject)"

    def test_parse_missing_sender(self, client: GmailClient) -> None:
        raw = {
            "id": "x",
            "snippet": "",
            "labelIds": [],
            "payload": {"headers": [{"name": "Subject", "value": "Hi"}]},
        }
        msg = client._parse(raw)
        assert msg.sender == "(unknown)"


# ---------------------------------------------------------------------------
# GmailMultiClient.from_env
# ---------------------------------------------------------------------------

class TestGmailMultiClientFromEnv:
    def test_raises_when_no_accounts_and_no_tokens(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.delenv("GMAIL_ACCOUNTS", raising=False)
        with patch("gmail.load_dotenv"), \
             patch("gmail.discover_accounts", return_value=[]), \
             pytest.raises(ConfigError, match="No authenticated accounts"):
            GmailMultiClient.from_env(env_file=tmp_path / ".env")

    def test_uses_discovered_accounts(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        with patch("gmail.load_dotenv"), \
             patch("gmail.discover_accounts", return_value=["a@gmail.com"]), \
             patch("gmail.GmailClient") as MockClient:
            MockClient.return_value = MagicMock()
            nina = GmailMultiClient.from_env()
            assert nina.accounts == ["a@gmail.com"]


# ---------------------------------------------------------------------------
# GmailMultiClient operations
# ---------------------------------------------------------------------------

class TestGmailMultiClientOperations:
    @pytest.fixture()
    def nina(self) -> GmailMultiClient:
        accounts = ["a@gmail.com", "b@gmail.com"]
        with patch("gmail.GmailClient") as MockClient:
            instances: dict[str, MagicMock] = {}

            def make_client(account: str, *_) -> MagicMock:  # type: ignore[no-untyped-def]
                m = MagicMock()
                m.account = account
                instances[account] = m
                return m

            MockClient.side_effect = make_client
            nina = GmailMultiClient(accounts, Path("tokens"))
            nina._test_mocks = instances  # type: ignore[attr-defined]
            return nina

    def test_list_unread_all_accounts(self, nina: GmailMultiClient) -> None:
        nina._test_mocks["a@gmail.com"].list_unread.return_value = [  # type: ignore[attr-defined]
            Message("1", "a@gmail.com", "Sub A", "x@x.com", "Mon, 1 Jan", "snip", False)
        ]
        nina._test_mocks["b@gmail.com"].list_unread.return_value = [  # type: ignore[attr-defined]
            Message("2", "b@gmail.com", "Sub B", "y@y.com", "Tue, 2 Jan", "snip", False)
        ]
        msgs = nina.list_unread()
        assert len(msgs) == 2
        assert {m.account for m in msgs} == {"a@gmail.com", "b@gmail.com"}

    def test_list_unread_single_account(self, nina: GmailMultiClient) -> None:
        nina._test_mocks["a@gmail.com"].list_unread.return_value = [  # type: ignore[attr-defined]
            Message("1", "a@gmail.com", "Sub A", "x@x.com", "Mon, 1 Jan", "snip", False)
        ]
        msgs = nina.list_unread(account="a@gmail.com")
        assert len(msgs) == 1
        nina._test_mocks["b@gmail.com"].list_unread.assert_not_called()  # type: ignore[attr-defined]

    def test_search_across_all_accounts(self, nina: GmailMultiClient) -> None:
        nina._test_mocks["a@gmail.com"].search.return_value = []  # type: ignore[attr-defined]
        nina._test_mocks["b@gmail.com"].search.return_value = [  # type: ignore[attr-defined]
            Message("3", "b@gmail.com", "Found", "z@z.com", "Wed, 3 Jan", "snip", True)
        ]
        msgs = nina.search("subject:found")
        assert len(msgs) == 1

    def test_client_raises_for_unknown_account(self, nina: GmailMultiClient) -> None:
        with pytest.raises(ConfigError, match="not loaded"):
            nina.client("unknown@gmail.com")
