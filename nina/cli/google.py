"""`nina google auth|status|revoke` — Google service commands."""

import argparse
import sys

from nina.cli._env import credentials_file, tokens_dir
from nina.errors import AuthError
from nina.integrations.google.auth import (
    discover_accounts,
    is_authenticated,
    revoke,
    run_oauth_flow,
)


def cmd_auth(args: argparse.Namespace) -> None:  # noqa: ARG001
    print("Opening browser for Google authentication...")
    print("Select the account you want to add to Nina.\n")
    try:
        email = run_oauth_flow(credentials_file(), tokens_dir())
        print(f"\nDone — {email} is now authenticated.")
    except AuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args: argparse.Namespace) -> None:  # noqa: ARG001
    td = tokens_dir()
    accounts = discover_accounts(td)
    if not accounts:
        print("No authenticated accounts found. Run: nina google auth")
        return
    for account in accounts:
        ok = is_authenticated(account, td)
        mark = "\u2713" if ok else "\u2717 (expired)"
        print(f"  {mark}  {account}")


def cmd_revoke(args: argparse.Namespace) -> None:
    revoke(args.account, tokens_dir())


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("google", help="Google service commands")
    g = p.add_subparsers(dest="action", required=True)

    g.add_parser("auth", help="Authenticate with Google OAuth").set_defaults(
        func=cmd_auth
    )

    g.add_parser(
        "status", help="Show authentication status for Google accounts"
    ).set_defaults(func=cmd_status)

    p_revoke = g.add_parser(
        "revoke", help="Remove stored Google token for an account"
    )
    p_revoke.add_argument("account", help="Email address to revoke")
    p_revoke.set_defaults(func=cmd_revoke)
