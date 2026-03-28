"""Nina — personal assistant CLI."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from nina.errors import AuthError, TelegramError
from nina.google.auth import discover_accounts, is_authenticated, revoke, run_oauth_flow
from nina.telegram.client import TgClient


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


# ── auth ──────────────────────────────────────────────────────────────────────

def cmd_auth(args: argparse.Namespace) -> None:
    if args.provider == "google":
        print("Opening browser for Google authentication...")
        print("Select the account you want to add to Nina.\n")
        try:
            email = run_oauth_flow(_credentials_file(), _tokens_dir())
            print(f"\nDone — {email} is now authenticated.")
        except AuthError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.provider == "telegram":
        with TgClient.from_env() as tg:
            if tg.is_authorized():
                print(f"Already authenticated as: {tg.me()}")
                return
            phone = args.phone or input("Phone number (with country code, e.g. +5511...): ").strip()
            tg.authorize(phone)
            print(f"\nAuthenticated as: {tg.me()}")
            print("Session saved — no need to re-auth next time.")


# ── status ─────────────────────────────────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> None:
    if args.provider == "google":
        tokens_dir = _tokens_dir()
        accounts = discover_accounts(tokens_dir)
        if not accounts:
            print("No authenticated accounts found. Run: nina auth google")
            return
        for account in accounts:
            ok = is_authenticated(account, tokens_dir)
            mark = "✓" if ok else "✗ (expired)"
            print(f"  {mark}  {account}")

    elif args.provider == "telegram":
        try:
            with TgClient.from_env() as tg:
                if tg.is_authorized():
                    print(f"  ✓  {tg.me()}")
                else:
                    print("  ✗  not authenticated — run: nina auth telegram")
        except TelegramError as e:
            print(f"  ✗  {e}", file=sys.stderr)


# ── revoke ────────────────────────────────────────────────────────────────────

def cmd_revoke(args: argparse.Namespace) -> None:
    """Remove stored Google token for an account."""
    revoke(args.account, _tokens_dir())


# ── Console ───────────────────────────────────────────────────────────────────

def cmd_console(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Open the interactive console (requires daemon running)."""
    load_dotenv()
    from nina.console.runner import run
    run()


# ── Daemon ────────────────────────────────────────────────────────────────────

def cmd_daemon(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Start Nina in daemon mode (scheduler + HTTP server)."""
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")

    from nina.daemon.runner import run
    run()


# ── Parser ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="nina",
        description="Nina — personal assistant CLI",
    )
    sub = parser.add_subparsers(dest="command")

    p_auth = sub.add_parser("auth", help="Authenticate a provider  (google | telegram)")
    p_auth.add_argument("provider", choices=["google", "telegram"])
    p_auth.add_argument("--phone", help="Telegram: phone number with country code")
    p_auth.set_defaults(func=cmd_auth)

    p_status = sub.add_parser("status", help="Show auth status for a provider  (google | telegram)")
    p_status.add_argument("provider", choices=["google", "telegram"])
    p_status.set_defaults(func=cmd_status)

    p_revoke = sub.add_parser("revoke", help="Remove stored Google token for an account")
    p_revoke.add_argument("account", help="Email address to revoke")
    p_revoke.set_defaults(func=cmd_revoke)

    p_console = sub.add_parser("console", help="Open interactive console (requires daemon)")
    p_console.set_defaults(func=cmd_console)

    p_daemon = sub.add_parser("daemon", help="Start Nina in daemon mode (scheduler + HTTP)")
    p_daemon.set_defaults(func=cmd_daemon)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)
