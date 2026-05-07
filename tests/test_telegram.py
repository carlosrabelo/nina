# tests/test_telegram.py
"""Tests for the Telegram client."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nina.integrations.telegram.client import Dialog, TgClient, TgMessage, _entity_name, _fmt_date


class TestFmtDate:
    def test_formats_datetime(self) -> None:
        dt = datetime(2026, 3, 27, 14, 30, tzinfo=timezone.utc)
        result = _fmt_date(dt)
        assert len(result) == 16  # "YYYY-MM-DD HH:MM"
        assert result[4] == "-" and result[7] == "-" and result[10] == " "

    def test_returns_empty_for_none(self) -> None:
        assert _fmt_date(None) == ""


class TestTgClientFromEnv:
    def test_raises_when_api_id_missing(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
        monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
        from nina.errors import TelegramError
        with patch("nina.integrations.telegram.client.load_dotenv"), \
             pytest.raises(TelegramError, match="TELEGRAM_API_ID"):
            TgClient.from_env()

    def test_raises_when_api_id_not_a_number(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("TELEGRAM_API_ID", "notanumber")
        monkeypatch.setenv("TELEGRAM_API_HASH", "abc")
        from nina.errors import TelegramError
        with patch("nina.integrations.telegram.client.load_dotenv"), \
             patch("nina.integrations.telegram.client.TelethonClient"), \
             pytest.raises(TelegramError, match="must be a number"):
            TgClient.from_env()

    def test_creates_client_with_valid_env(self, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("TELEGRAM_API_ID", "12345")
        monkeypatch.setenv("TELEGRAM_API_HASH", "abc123")
        monkeypatch.setenv("TOKENS_DIR", str(tmp_path))
        with patch("nina.integrations.telegram.client.load_dotenv"), \
             patch("nina.integrations.telegram.client.TelethonClient") as MockTelethon:
            MockTelethon.return_value = MagicMock()
            client = TgClient.from_env()
            assert client is not None
            MockTelethon.assert_called_once()
            call_args = MockTelethon.call_args
            assert call_args[0][1] == 12345
            assert call_args[0][2] == "abc123"


@pytest.fixture()
def tg_client(tmp_path: Path) -> TgClient:
    with patch("nina.integrations.telegram.client.TelethonClient") as MockTelethon:
        mock_inner = MagicMock()
        MockTelethon.return_value = mock_inner
        client = TgClient(12345, "abc", tmp_path / "telegram")
        client._client = mock_inner
        return client


class TestTgClientDialogs:
    def test_list_dialogs_maps_user(self, tg_client: TgClient) -> None:
        from telethon.tl.types import User as TgUser
        mock_user = MagicMock(spec=TgUser)
        mock_user.first_name = "João"
        mock_user.last_name = "Silva"

        mock_dialog = MagicMock()
        mock_dialog.id = 123
        mock_dialog.entity = mock_user
        mock_dialog.unread_count = 2

        tg_client._client.get_dialogs.return_value = [mock_dialog]
        dialogs = tg_client.list_dialogs()

        assert len(dialogs) == 1
        assert dialogs[0].name == "João Silva"
        assert dialogs[0].unread_count == 2
        assert dialogs[0].kind == "user"

    def test_list_dialogs_returns_empty(self, tg_client: TgClient) -> None:
        tg_client._client.get_dialogs.return_value = []
        assert tg_client.list_dialogs() == []


class TestTgClientMessages:
    def test_get_messages_skips_media_only(self, tg_client: TgClient) -> None:
        mock_entity = MagicMock()
        tg_client._client.get_entity.return_value = mock_entity

        msg_with_text = MagicMock()
        msg_with_text.id = 1
        msg_with_text.text = "Oi"
        msg_with_text.out = False
        msg_with_text.chat_id = 99
        msg_with_text.sender = MagicMock()
        msg_with_text.sender.first_name = "Ana"
        msg_with_text.sender.last_name = None
        msg_with_text.date = datetime(2026, 3, 27, tzinfo=timezone.utc)

        msg_no_text = MagicMock()
        msg_no_text.text = None

        tg_client._client.get_messages.return_value = [msg_with_text, msg_no_text]
        messages = tg_client.get_messages(99)

        assert len(messages) == 1
        assert messages[0].text == "Oi"

    def test_send_message_calls_telethon(self, tg_client: TgClient) -> None:
        mock_entity = MagicMock()
        tg_client._client.get_entity.return_value = mock_entity
        tg_client.send_message(99, "Olá!")
        tg_client._client.send_message.assert_called_once_with(mock_entity, "Olá!")
