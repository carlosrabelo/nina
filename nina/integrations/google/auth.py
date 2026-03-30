# nina/google/auth.py
"""Google OAuth flow management — one token file per account."""

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from nina.errors import AuthError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]


def run_oauth_flow(credentials_file: Path, tokens_dir: Path) -> str:
    """Open browser OAuth flow, auto-discover the authenticated email, save token.

    Returns:
        The authenticated email address.

    Raises:
        AuthError: If credentials file is missing, the flow fails, or email
                   cannot be retrieved.
    """
    if not credentials_file.exists():
        raise AuthError(
            "",
            f"credentials file not found: {credentials_file}\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials.",
        )

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        creds = flow.run_local_server(port=0)
    except Exception as e:
        raise AuthError("", f"OAuth flow failed: {e}") from e

    # Discover which email was just authenticated via the Gmail profile endpoint.
    try:
        svc = build("gmail", "v1", credentials=creds)
        profile = svc.users().getProfile(userId="me").execute()
        email: str = profile["emailAddress"]
    except Exception as e:
        raise AuthError("", f"failed to retrieve account email: {e}") from e

    # Save token with the email embedded so we can recover it on next startup.
    tokens_dir.mkdir(parents=True, exist_ok=True)
    token_data = json.loads(creds.to_json())
    token_data["_nina_email"] = email
    token_file = tokens_dir / f"{_safe_name(email)}.json"
    token_file.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    print(f"  Token saved for {email}")

    return email


def get_credentials(account: str, tokens_dir: Path) -> Credentials:
    """Return valid (possibly refreshed) credentials for *account*.

    Raises:
        AuthError: If no token is found or refresh fails.
    """
    token_file = tokens_dir / f"{_safe_name(account)}.json"

    if not token_file.exists():
        raise AuthError(account, "not authenticated. Run: ./nina.py auth")

    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    # If the token predates a scope addition, force re-auth.
    # Read scopes from the raw JSON because creds.scopes is None after loading from file.
    token_data = json.loads(token_file.read_text(encoding="utf-8"))
    raw_scopes = token_data.get("scopes", "")
    saved_scopes = set(raw_scopes.split() if isinstance(raw_scopes, str) else raw_scopes)
    if saved_scopes and not set(SCOPES).issubset(saved_scopes):
        raise AuthError(
            account,
            "token is missing required scopes — run: ./nina.py auth  (to re-authenticate)",
        )

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Preserve the _nina_email field while updating the token.
                existing = json.loads(token_file.read_text(encoding="utf-8"))
                updated = json.loads(creds.to_json())
                updated["_nina_email"] = existing.get("_nina_email", account)
                token_file.write_text(json.dumps(updated, indent=2), encoding="utf-8")
            except Exception as e:
                raise AuthError(account, f"token refresh failed: {e}") from e
        else:
            raise AuthError(
                account, "token expired and no refresh token. Run: ./nina.py auth"
            )

    return creds


def discover_accounts(tokens_dir: Path) -> list[str]:
    """Return all authenticated emails found in *tokens_dir*."""
    accounts: list[str] = []
    for token_file in sorted(tokens_dir.glob("*.json")):
        try:
            data = json.loads(token_file.read_text(encoding="utf-8"))
            email = data.get("_nina_email")
            if email:
                accounts.append(email)
        except (json.JSONDecodeError, OSError):
            continue
    return accounts


def is_authenticated(account: str, tokens_dir: Path) -> bool:
    """Return True if *account* has a stored token with a refresh token."""
    token_file = tokens_dir / f"{_safe_name(account)}.json"
    if not token_file.exists():
        return False
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    return bool(creds.valid or creds.refresh_token)


def revoke(account: str, tokens_dir: Path) -> None:
    """Delete the stored token for *account*."""
    token_file = tokens_dir / f"{_safe_name(account)}.json"
    if token_file.exists():
        token_file.unlink()
        print(f"  Token removed for {account}")
    else:
        print(f"  No token found for {account}")


def _safe_name(account: str) -> str:
    """Convert an email to a safe filename (replaces @ and .)."""
    return account.replace("@", "_at_").replace(".", "_")
