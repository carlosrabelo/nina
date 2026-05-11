"""Top-level argparse wiring for `nina`."""

import argparse

from nina.cli import (
    auth,
    calendar,
    console,
    daemon,
    email_learning,
    gmail,
    llm,
    make_aliases,
    revoke,
    status,
    telegram,
)
from nina.cli._env import load_project_dotenv


def main() -> None:
    load_project_dotenv()
    parser = argparse.ArgumentParser(
        prog="nina",
        description="Nina — personal assistant CLI",
    )
    sub = parser.add_subparsers(dest="command")

    auth.register(sub)
    status.register(sub)
    revoke.register(sub)
    console.register(sub)
    daemon.register(sub)
    make_aliases.register(sub)
    gmail.register(sub)
    email_learning.register(sub)
    calendar.register(sub)
    telegram.register(sub)
    llm.register(sub)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)
