# tests/test_telegram_bot.py
"""Tests for the Telegram Bot batch processor."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nina.errors import TelegramError
from nina.integrations.telegram.bot import load_offset, run_batch_from_env, save_offset


class TestOffsetPersistence:
    def test_load_returns_zero_when_no_file(self, tmp_path: Path) -> None:
        assert load_offset(tmp_path) == 0

    def test_save_then_load(self, tmp_path: Path) -> None:
        save_offset(tmp_path, 42)
        assert load_offset(tmp_path) == 42

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "dir"
        save_offset(nested, 7)
        assert load_offset(nested) == 7

    def test_save_overwrites_previous(self, tmp_path: Path) -> None:
        save_offset(tmp_path, 10)
        save_offset(tmp_path, 99)
        assert load_offset(tmp_path) == 99


class TestRunBatchFromEnvConfig:
    def test_raises_when_bot_token_missing(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
        with patch("nina.integrations.telegram.bot.load_dotenv"), \
             pytest.raises(TelegramError, match="BOT_TOKEN"):
            run_batch_from_env()

    def test_raises_when_owner_id_missing(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
        monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
        with patch("nina.integrations.telegram.bot.load_dotenv"), \
             pytest.raises(TelegramError, match="OWNER_ID"):
            run_batch_from_env()

    def test_raises_when_owner_id_not_a_number(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "notanumber")
        with patch("nina.integrations.telegram.bot.load_dotenv"), \
             pytest.raises(TelegramError, match="must be a number"):
            run_batch_from_env()

    def test_runs_batch_with_valid_config(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
        monkeypatch.setenv("TELEGRAM_OWNER_ID", "999")
        monkeypatch.setenv("TOKENS_DIR", str(tmp_path))
        with patch("nina.integrations.telegram.bot.load_dotenv"), \
             patch("nina.integrations.telegram.bot.asyncio.run", return_value=0) as mock_run:
            result = run_batch_from_env()
            assert result == 0
            mock_run.assert_called_once()


class TestRunBatch:
    @pytest.mark.asyncio
    async def test_saves_offset_after_updates(self, tmp_path: Path) -> None:
        from nina.integrations.telegram.bot import run_batch

        mock_update = MagicMock()
        mock_update.update_id = 10
        mock_update.message = MagicMock()
        mock_update.message.chat_id = 999

        mock_app = AsyncMock()
        mock_app.__aenter__ = AsyncMock(return_value=mock_app)
        mock_app.__aexit__ = AsyncMock(return_value=False)
        mock_app.bot.get_updates = AsyncMock(return_value=[mock_update])
        mock_app.process_update = AsyncMock()

        with patch("nina.integrations.telegram.bot.Application") as MockApp:
            MockApp.builder.return_value.token.return_value.build.return_value = mock_app
            await run_batch("token", 999, tmp_path)

        assert load_offset(tmp_path) == 11

    @pytest.mark.asyncio
    async def test_skips_updates_from_non_owner(self, tmp_path: Path) -> None:
        from nina.integrations.telegram.bot import run_batch

        mock_update = MagicMock()
        mock_update.update_id = 5
        mock_update.message = MagicMock()
        mock_update.message.chat_id = 111

        mock_app = AsyncMock()
        mock_app.__aenter__ = AsyncMock(return_value=mock_app)
        mock_app.__aexit__ = AsyncMock(return_value=False)
        mock_app.bot.get_updates = AsyncMock(return_value=[mock_update])
        mock_app.process_update = AsyncMock()

        with patch("nina.integrations.telegram.bot.Application") as MockApp:
            MockApp.builder.return_value.token.return_value.build.return_value = mock_app
            count = await run_batch("token", 999, tmp_path)

        assert count == 0
        mock_app.process_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_updates(self, tmp_path: Path) -> None:
        from nina.integrations.telegram.bot import run_batch

        mock_app = AsyncMock()
        mock_app.__aenter__ = AsyncMock(return_value=mock_app)
        mock_app.__aexit__ = AsyncMock(return_value=False)
        mock_app.bot.get_updates = AsyncMock(return_value=[])

        with patch("nina.integrations.telegram.bot.Application") as MockApp:
            MockApp.builder.return_value.token.return_value.build.return_value = mock_app
            count = await run_batch("token", 999, tmp_path)

        assert count == 0
