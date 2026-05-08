"""Top-level argparse wiring for `nina`."""

import argparse

from nina.cli import (
    auth,
    calendar,
    console,
    daemon,
    gmail,
    llm,
    make_aliases,
    migrate,
    revoke,
    status,
    telegram,
)


def main() -> None:
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
    calendar.register(sub)
    telegram.register(sub)
    llm.register(sub)
    migrate.register(sub)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)
