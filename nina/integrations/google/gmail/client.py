# nina/google/gmail/client.py
"""Gmail API client supporting multiple accounts."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from nina.integrations.google.auth import discover_accounts, get_credentials
from nina.errors import ConfigError, GmailError


@dataclass
class Message:
    """A Gmail message with the most relevant fields."""

    id: str
    account: str
    subject: str
    sender: str
    date: str
    snippet: str
    is_read: bool
    labels: list[str] = field(default_factory=list)


class GmailClient:
    """Gmail client for a single account."""

    def __init__(self, account: str, tokens_dir: Path) -> None:
        self.account = account
        creds = get_credentials(account, tokens_dir)
        self._svc = build("gmail", "v1", credentials=creds)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_latest(self, max_results: int = 10) -> list[Message]:
        """Return the most recent messages regardless of read status."""
        return self._search("", max_results)

    def list_unread(self, max_results: int = 20) -> list[Message]:
        """Return up to *max_results* unread messages."""
        return self._search("is:unread", max_results)

    def search(self, query: str, max_results: int = 20) -> list[Message]:
        """Search messages using Gmail query syntax."""
        return self._search(query, max_results)

    def get_message(self, message_id: str) -> Message:
        """Fetch full details for a single message by ID."""
        try:
            raw = (
                self._svc.users()
                .messages()
                .get(userId="me", id=message_id, format="metadata")
                .execute()
            )
        except HttpError as e:
            raise GmailError(self.account, str(e)) from e
        return self._parse(raw)

    def mark_as_read(self, message_id: str) -> None:
        """Remove the UNREAD label from a message."""
        try:
            self._svc.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
        except HttpError as e:
            raise GmailError(self.account, str(e)) from e

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _search(self, query: str, max_results: int) -> list[Message]:
        try:
            result = (
                self._svc.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
        except HttpError as e:
            raise GmailError(self.account, str(e)) from e

        items = result.get("messages", [])
        messages: list[Message] = []
        for item in items:
            try:
                raw = (
                    self._svc.users()
                    .messages()
                    .get(userId="me", id=item["id"], format="metadata")
                    .execute()
                )
                messages.append(self._parse(raw))
            except HttpError:
                continue
        return messages

    def _parse(self, raw: dict) -> Message:  # type: ignore[type-arg]
        headers = {
            h["name"].lower(): h["value"]
            for h in raw.get("payload", {}).get("headers", [])
        }
        labels = raw.get("labelIds", [])
        return Message(
            id=raw["id"],
            account=self.account,
            subject=headers.get("subject", "(no subject)"),
            sender=headers.get("from", "(unknown)"),
            date=headers.get("date", ""),
            snippet=raw.get("snippet", ""),
            is_read="UNREAD" not in labels,
            labels=labels,
        )


class GmailMultiClient:
    """Manages Gmail clients for multiple accounts simultaneously."""

    def __init__(self, accounts: list[str], tokens_dir: Path) -> None:
        if not accounts:
            raise ConfigError("No Gmail accounts found. Run: ./nina.py auth")
        self._clients: dict[str, GmailClient] = {
            account: GmailClient(account, tokens_dir) for account in accounts
        }

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "GmailMultiClient":
        """Create from environment / token discovery."""
        load_dotenv(env_file)
        tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
        accounts = discover_accounts(tokens_dir)

        if not accounts:
            raise ConfigError(
                "No authenticated accounts found.\n"
                "Run: ./nina.py auth  (repeat for each account)"
            )

        return cls(accounts, tokens_dir)

    # ------------------------------------------------------------------
    # Multi-account operations
    # ------------------------------------------------------------------

    @property
    def accounts(self) -> list[str]:
        return list(self._clients.keys())

    def client(self, account: str) -> GmailClient:
        """Return the client for a specific account."""
        if account not in self._clients:
            raise ConfigError(
                f"Account {account!r} not loaded. Known: {self.accounts}"
            )
        return self._clients[account]

    def list_unread(
        self,
        account: str | None = None,
        max_results: int = 20,
    ) -> list[Message]:
        """List unread messages across all accounts (or a specific one)."""
        clients = (
            [self._clients[account]] if account else list(self._clients.values())
        )
        messages: list[Message] = []
        for c in clients:
            messages.extend(c.list_unread(max_results))
        return messages

    def search(
        self,
        query: str,
        account: str | None = None,
        max_results: int = 20,
    ) -> list[Message]:
        """Search across all accounts (or a specific one)."""
        clients = (
            [self._clients[account]] if account else list(self._clients.values())
        )
        messages: list[Message] = []
        for c in clients:
            messages.extend(c.search(query, max_results))
        return messages
