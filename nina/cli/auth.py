"""`nina auth google|telegram` — authenticate a provider."""

import argparse
import sys

from nina.cli._env import credentials_file, tokens_dir
from nina.errors import AuthError
from nina.integrations.google.auth import run_oauth_flow


def cmd_auth(args: argparse.Namespace) -> None:
    if args.provider == "google":
        print("Opening browser for Google authentication...")
        print("Select the account you want to add to Nina.\n")
        try:
            email = run_oauth_flow(credentials_file(), tokens_dir())
            print(f"\nDone — {email} is now authenticated.")
        except AuthError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.provider == "telegram":
        from nina.integrations.telegram.client import TgClient
        with TgClient.from_env() as tg:
            if tg.is_authorized():
                print(f"Already authenticated as: {tg.me()}")
                return
            phone = args.phone or input(
                "Phone number (with country code, e.g. +5511...): "
            ).strip()
            tg.authorize(phone)
            print(f"\nAuthenticated as: {tg.me()}")
            print("Session saved — no need to re-auth next time.")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("auth", help="Authenticate a provider  (google | telegram)")
    p.add_argument("provider", choices=["google", "telegram"])
    p.add_argument("--phone", help="Telegram: phone number with country code")
    p.set_defaults(func=cmd_auth)
