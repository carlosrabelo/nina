# tests/conftest.py
"""Shared pytest fixtures."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def fake_credentials(tmp_path: Path) -> Path:
    """A minimal fake credentials.json (OAuth client secret format)."""
    creds = tmp_path / "credentials.json"
    creds.write_text(
        '{"installed":{"client_id":"fake","client_secret":"fake",'
        '"redirect_uris":["urn:ietf:wg:oauth:2.0:oob"],'
        '"auth_uri":"https://accounts.google.com/o/oauth2/auth",'
        '"token_uri":"https://oauth2.googleapis.com/token"}}',
        encoding="utf-8",
    )
    return creds


@pytest.fixture()
def fake_token(tmp_path: Path) -> Path:
    """Write a fake (but structurally valid) token file and return its dir."""
    tokens_dir = tmp_path / "tokens"
    tokens_dir.mkdir()
    token = tokens_dir / "user_at_gmail_com.json"
    token.write_text(
        '{"token":"fake","refresh_token":"fake-refresh",'
        '"token_uri":"https://oauth2.googleapis.com/token",'
        '"client_id":"fake","client_secret":"fake","scopes":['
        '"https://www.googleapis.com/auth/gmail.readonly",'
        '"https://www.googleapis.com/auth/gmail.modify"]}',
        encoding="utf-8",
    )
    return tokens_dir


@pytest.fixture()
def mock_gmail_service() -> MagicMock:
    """A mock of the Gmail API service object."""
    svc = MagicMock()
    return svc
