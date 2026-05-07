"""`nina status google|telegram` — show authentication status."""

import argparse
import sys

from nina.cli._env import tokens_dir
from nina.errors import TelegramError
from nina.integrations.google.auth import discover_accounts, is_authenticated


def cmd_status(args: argparse.Namespace) -> None:
    if args.provider == "google":
        td = tokens_dir()
        accounts = discover_accounts(td)
        if not accounts:
            print("No authenticated accounts found. Run: nina auth google")
            return
        for account in accounts:
            ok = is_authenticated(account, td)
            mark = "✓" if ok else "✗ (expired)"
            print(f"  {mark}  {account}")

    elif args.provider == "telegram":
        try:
            from nina.integrations.telegram.client import TgClient
            with TgClient.from_env() as tg:
                if tg.is_authorized():
                    print(f"  ✓  {tg.me()}")
                else:
                    print("  ✗  not authenticated — run: nina auth telegram")
        except TelegramError as e:
            print(f"  ✗  {e}", file=sys.stderr)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "status", help="Show auth status for a provider  (google | telegram)"
    )
    p.add_argument("provider", choices=["google", "telegram"])
    p.set_defaults(func=cmd_status)
