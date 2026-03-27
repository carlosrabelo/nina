# errors.py
"""Custom exception types for Nina."""


class NinaError(Exception):
    """Base exception for all Nina errors."""


class AuthError(NinaError):
    """Raised when OAuth authentication fails."""

    def __init__(self, account: str, message: str) -> None:
        self.account = account
        super().__init__(f"auth failed for {account}: {message}")


class GmailError(NinaError):
    """Raised when a Gmail API call fails."""

    def __init__(self, account: str, message: str) -> None:
        self.account = account
        super().__init__(f"gmail error for {account}: {message}")


class CalendarError(NinaError):
    """Raised when a Google Calendar API call fails."""

    def __init__(self, account: str, message: str) -> None:
        self.account = account
        super().__init__(f"calendar error for {account}: {message}")


class TelegramError(NinaError):
    """Raised when a Telegram operation fails."""


class ConfigError(NinaError):
    """Raised when required configuration is missing or invalid."""
