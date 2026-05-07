"""`nina revoke <account>` — remove a stored Google token."""

import argparse

from nina.cli._env import tokens_dir
from nina.integrations.google.auth import revoke


def cmd_revoke(args: argparse.Namespace) -> None:
    revoke(args.account, tokens_dir())


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("revoke", help="Remove stored Google token for an account")
    p.add_argument("account", help="Email address to revoke")
    p.set_defaults(func=cmd_revoke)
