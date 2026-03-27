#!/usr/bin/env python3
"""Nina — personal assistant CLI."""

import os
import sys
from pathlib import Path

_venv_python = Path(__file__).resolve().parent / ".venv" / "bin" / "python"
if _venv_python.exists() and Path(sys.executable).resolve() != _venv_python.resolve():
    os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)

import argparse

from dotenv import load_dotenv

from auth import discover_accounts, is_authenticated, revoke, run_oauth_flow
from calendar_client import CalendarClient
from errors import AuthError, CalendarError, ConfigError, GmailError
from gmail import GmailMultiClient


def _tokens_dir() -> Path:
    load_dotenv()
    return Path(os.environ.get("TOKENS_DIR", "tokens"))


def _credentials_file() -> Path:
    load_dotenv()
    return Path(
        os.environ.get(
            "GOOGLE_CREDENTIALS_FILE", "credentials/credentials.json"
        )
    )


def cmd_auth(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Open browser OAuth flow and save the token (repeat for each account)."""
    print("Opening browser for Google authentication...")
    print("Select the account you want to add to Nina.\n")
    try:
        email = run_oauth_flow(_credentials_file(), _tokens_dir())
        print(f"\nDone — {email} is now authenticated.")
    except AuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Show authentication status for all discovered accounts."""
    tokens_dir = _tokens_dir()
    accounts = discover_accounts(tokens_dir)

    if not accounts:
        print("No authenticated accounts found. Run: ./nina.py auth")
        return

    for account in accounts:
        ok = is_authenticated(account, tokens_dir)
        mark = "✓" if ok else "✗ (expired)"
        print(f"  {mark}  {account}")


def cmd_revoke(args: argparse.Namespace) -> None:
    """Remove stored token for an account."""
    revoke(args.account, _tokens_dir())


def cmd_calendars(args: argparse.Namespace) -> None:
    """List all calendars in one or all accounts."""
    tokens_dir = _tokens_dir()
    accounts = [args.account] if args.account else discover_accounts(tokens_dir)

    if not accounts:
        print("No authenticated accounts found. Run: ./nina.py auth")
        sys.exit(1)

    for account in accounts:
        try:
            calendars = CalendarClient(account, tokens_dir).list_calendars()
        except (AuthError, CalendarError) as e:
            print(f"Error: {e}", file=sys.stderr)
            continue

        print(f"── {account} {'─' * (50 - len(account))}")
        for cal in calendars:
            marker = " (primary)" if cal.primary else ""
            print(f"  [{cal.access_role}]  {cal.name}{marker}")
            print(f"           id: {cal.id}")
        print()


def cmd_events(args: argparse.Namespace) -> None:
    """List upcoming Calendar events for one or all accounts."""
    tokens_dir = _tokens_dir()
    accounts = [args.account] if args.account else discover_accounts(tokens_dir)

    if not accounts:
        print("No authenticated accounts found. Run: ./nina.py auth")
        sys.exit(1)

    for account in accounts:
        try:
            events = CalendarClient(account, tokens_dir).list_upcoming(
                args.limit, args.calendar
            )
        except (AuthError, CalendarError) as e:
            print(f"Error: {e}", file=sys.stderr)
            continue

        print(f"── {account} {'─' * (50 - len(account))}")
        if not events:
            print("  (no upcoming events)")
        for ev in events:
            print(f"  {ev.start}")
            print(f"  {ev.title}")
            if ev.location:
                print(f"  Local   : {ev.location}")
            print()


def cmd_latest(args: argparse.Namespace) -> None:
    """Show headers of the most recent emails from one or all accounts."""
    try:
        nina = GmailMultiClient.from_env()
        accounts = [args.account] if args.account else nina.accounts
        for account in accounts:
            messages = nina.client(account).list_latest(max_results=args.limit)
            print(f"── {account} {'─' * (50 - len(account))}")
            if not messages:
                print("  (no messages)")
            for msg in messages:
                status = " ●" if not msg.is_read else "  "
                print(f"{status} {msg.date}")
                print(f"   From    : {msg.sender}")
                print(f"   Subject : {msg.subject}")
                print()
    except (ConfigError, AuthError, GmailError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_unread(args: argparse.Namespace) -> None:
    """List unread messages."""
    try:
        nina = GmailMultiClient.from_env()
        messages = nina.list_unread(account=args.account, max_results=args.limit)
    except (ConfigError, AuthError, GmailError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not messages:
        print("No unread messages.")
        return

    for msg in messages:
        prefix = f"[{msg.account}]  " if not args.account else ""
        print(f"{prefix}{msg.sender}")
        print(f"  Subject : {msg.subject}")
        print(f"  Preview : {msg.snippet[:80]}")
        print()


def cmd_search(args: argparse.Namespace) -> None:
    """Search messages with Gmail query syntax."""
    try:
        nina = GmailMultiClient.from_env()
        messages = nina.search(args.query, account=args.account, max_results=args.limit)
    except (ConfigError, AuthError, GmailError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not messages:
        print("No messages found.")
        return

    for msg in messages:
        prefix = f"[{msg.account}]  " if not args.account else ""
        status = "" if msg.is_read else " [UNREAD]"
        print(f"{prefix}{status}{msg.sender}")
        print(f"  Subject : {msg.subject}")
        print(f"  Preview : {msg.snippet[:80]}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="nina",
        description="Nina — personal assistant CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # auth — no --account, you pick in the browser
    p_auth = sub.add_parser("auth", help="Add an account via Google OAuth (opens browser)")
    p_auth.set_defaults(func=cmd_auth)

    # status
    p_status = sub.add_parser("status", help="Show auth status for all accounts")
    p_status.set_defaults(func=cmd_status)

    # revoke
    p_revoke = sub.add_parser("revoke", help="Remove stored token for an account")
    p_revoke.add_argument("account", help="Email address to revoke")
    p_revoke.set_defaults(func=cmd_revoke)

    # calendars
    p_calendars = sub.add_parser("calendars", help="List all calendars in the account")
    p_calendars.add_argument("--account", help="Filter to a specific account")
    p_calendars.set_defaults(func=cmd_calendars)

    # events
    p_events = sub.add_parser("events", help="List upcoming Calendar events")
    p_events.add_argument("--account", help="Filter to a specific account")
    p_events.add_argument("--calendar", default="primary", help="Calendar ID (default: primary)")
    p_events.add_argument("--limit", type=int, default=10)
    p_events.set_defaults(func=cmd_events)

    # latest
    p_latest = sub.add_parser("latest", help="Show headers of the most recent emails")
    p_latest.add_argument("--account", help="Filter to a specific account")
    p_latest.add_argument("--limit", type=int, default=10)
    p_latest.set_defaults(func=cmd_latest)

    # unread
    p_unread = sub.add_parser("unread", help="List unread messages")
    p_unread.add_argument("--account", help="Filter to a specific account")
    p_unread.add_argument("--limit", type=int, default=20)
    p_unread.set_defaults(func=cmd_unread)

    # search
    p_search = sub.add_parser("search", help="Search messages (Gmail query syntax)")
    p_search.add_argument("query")
    p_search.add_argument("--account", help="Filter to a specific account")
    p_search.add_argument("--limit", type=int, default=20)
    p_search.set_defaults(func=cmd_search)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
