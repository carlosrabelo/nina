# nina/google/gmail/client.py
"""Gmail API client supporting multiple accounts."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from nina.errors import ConfigError, GmailError
from nina.integrations.google.auth import discover_accounts, get_credentials


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
    thread_id: str = ""


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

    def list_user_label_map(self) -> dict[str, str]:
        """Map Gmail label id → display name for **user** labels only."""
        try:
            lst = self._svc.users().labels().list(userId="me").execute()
        except HttpError as e:
            raise GmailError(self.account, str(e)) from e
        out: dict[str, str] = {}
        for lb in lst.get("labels", []):
            if lb.get("type") == "user" and lb.get("id") and lb.get("name") is not None:
                out[str(lb["id"])] = str(lb["name"])
        return out

    def search_paged(
        self,
        query: str,
        *,
        max_messages: int,
        page_size: int = 100,
    ) -> list[Message]:
        """Like :meth:`search`, but follows ``nextPageToken`` until *max_messages*."""
        messages: list[Message] = []
        page_token: str | None = None
        page_size = max(1, min(500, page_size))
        max_messages = max(1, max_messages)

        while len(messages) < max_messages:
            batch = min(page_size, max_messages - len(messages))
            req_kwargs: dict = {"userId": "me", "q": query, "maxResults": batch}
            if page_token:
                req_kwargs["pageToken"] = page_token
            try:
                result = self._svc.users().messages().list(**req_kwargs).execute()
            except HttpError as e:
                raise GmailError(self.account, str(e)) from e

            items = result.get("messages", [])
            for item in items:
                if len(messages) >= max_messages:
                    break
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

            page_token = result.get("nextPageToken")
            if not page_token or not items:
                break

        return messages

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

    def ensure_user_label(self, display_name: str) -> str:
        """Return the Gmail label id for *display_name*, creating it if missing."""
        try:
            lst = self._svc.users().labels().list(userId="me").execute()
        except HttpError as e:
            raise GmailError(self.account, str(e)) from e
        for lb in lst.get("labels", []):
            if lb.get("type") == "user" and lb.get("name") == display_name:
                return str(lb["id"])
        try:
            body = {
                "name": display_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            created = (
                self._svc.users().labels().create(userId="me", body=body).execute()
            )
            return str(created["id"])
        except HttpError as e:
            raise GmailError(self.account, str(e)) from e

    def apply_label(
        self,
        message_id: str,
        label_id: str,
        *,
        archive_inbox: bool = True,
    ) -> None:
        """Attach a user label; optionally remove INBOX (archive out of inbox)."""
        body: dict[str, list[str]] = {"addLabelIds": [label_id]}
        if archive_inbox:
            body["removeLabelIds"] = ["INBOX"]
        try:
            self._svc.users().messages().modify(
                userId="me", id=message_id, body=body
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
            thread_id=str(raw.get("threadId", "") or ""),
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
