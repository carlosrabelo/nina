# nina/telegram/client.py
"""Telegram client using Telethon (MTProto — acts as a real user account)."""

import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telethon.sync import TelegramClient as TelethonClient
from telethon.tl.types import Channel, Chat, User

from nina.errors import TelegramError


@dataclass
class Dialog:
    """A Telegram chat/group/channel entry."""

    id: int
    name: str
    unread_count: int
    kind: str  # "user", "group", "channel"


@dataclass
class TgMessage:
    """A Telegram message."""

    id: int
    chat_id: int
    chat_name: str
    sender: str
    text: str
    date: str
    is_outgoing: bool


class TgClient:
    """Telegram client wrapping Telethon for on-demand (non-loop) use."""

    def __init__(self, api_id: int, api_hash: str, session_path: Path) -> None:
        self._client = TelethonClient(str(session_path), api_id, api_hash)

    # ------------------------------------------------------------------
    # Context manager — connect/disconnect automatically
    # ------------------------------------------------------------------

    def __enter__(self) -> "TgClient":
        self._client.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self._client.disconnect()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def is_authorized(self) -> bool:
        return bool(self._client.is_user_authorized())

    def authorize(self, phone: str) -> None:
        """Interactive auth: send code to *phone*, read it from stdin, sign in."""
        self._client.send_code_request(phone)
        code = input("Telegram verification code: ").strip()
        try:
            self._client.sign_in(phone, code)
        except Exception:
            # 2FA — ask for password
            password = input("Two-factor authentication password: ").strip()
            self._client.sign_in(password=password)

    def me(self) -> str:
        """Return the authenticated user's display name + phone."""
        user = self._client.get_me()
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        return f"{name} ({user.phone})"

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_dialogs(self, max_results: int = 20) -> list[Dialog]:
        """Return the most recent dialogs (chats, groups, channels)."""
        try:
            dialogs = self._client.get_dialogs(limit=max_results)
        except Exception as e:
            raise TelegramError(str(e)) from e

        result: list[Dialog] = []
        for d in dialogs:
            entity = d.entity
            if isinstance(entity, User):
                kind = "user"
                name = f"{entity.first_name or ''} {entity.last_name or ''}".strip()
            elif isinstance(entity, Channel):
                kind = "channel"
                name = entity.title
            else:
                kind = "group"
                name = entity.title if isinstance(entity, Chat) else str(d.name)
            result.append(
                Dialog(
                    id=d.id,
                    name=name or str(d.id),
                    unread_count=d.unread_count,
                    kind=kind,
                )
            )
        return result

    def get_messages(self, chat: int | str, max_results: int = 20) -> list[TgMessage]:
        """Return recent messages from *chat* (id, username, or phone)."""
        try:
            entity = self._client.get_entity(chat)
            messages = self._client.get_messages(entity, limit=max_results)
        except Exception as e:
            raise TelegramError(str(e)) from e

        chat_name = _entity_name(entity)
        result: list[TgMessage] = []
        for msg in messages:
            if msg.text is None:
                continue
            sender = _entity_name(msg.sender) if msg.sender else "?"
            result.append(
                TgMessage(
                    id=msg.id,
                    chat_id=msg.chat_id,
                    chat_name=chat_name,
                    sender=sender,
                    text=msg.text,
                    date=_fmt_date(msg.date),
                    is_outgoing=bool(msg.out),
                )
            )
        return result

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def send_message(self, chat: int | str, text: str) -> None:
        """Send *text* to *chat* (id, username, or phone)."""
        try:
            entity = self._client.get_entity(chat)
            self._client.send_message(entity, text)
        except Exception as e:
            raise TelegramError(str(e)) from e

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "TgClient":
        """Create from environment variables (loads .env automatically)."""
        load_dotenv(env_file)

        api_id_raw = os.environ.get("TELEGRAM_API_ID", "")
        api_hash = os.environ.get("TELEGRAM_API_HASH", "")

        if not api_id_raw or not api_hash:
            raise TelegramError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH are required in .env\n"
                "Get them at https://my.telegram.org → API Development Tools"
            )

        try:
            api_id = int(api_id_raw)
        except ValueError:
            raise TelegramError(f"TELEGRAM_API_ID must be a number, got: {api_id_raw!r}")

        tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
        tokens_dir.mkdir(parents=True, exist_ok=True)
        session_path = tokens_dir / "telegram"  # Telethon appends .session

        return cls(api_id, api_hash, session_path)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _entity_name(entity: object) -> str:
    if isinstance(entity, User):
        return f"{entity.first_name or ''} {entity.last_name or ''}".strip() or str(entity.id)
    if isinstance(entity, (Chat, Channel)):
        return entity.title
    return str(entity)


def _fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")
