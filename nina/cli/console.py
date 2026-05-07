"""`nina console` — interactive REPL (requires daemon running)."""

import argparse

from dotenv import load_dotenv


def cmd_console(args: argparse.Namespace) -> None:  # noqa: ARG001
    load_dotenv()
    from nina.core.console.runner import run
    run()


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("console", help="Open interactive console (requires daemon)")
    p.set_defaults(func=cmd_console)
