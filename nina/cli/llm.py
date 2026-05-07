"""`nina llm ping` — verify LLM connectivity and authentication."""

import argparse
import sys

from nina.core.llm.client import LLMClient
from nina.errors import LLMError


def cmd_ping(args: argparse.Namespace) -> None:  # noqa: ARG001
    try:
        client = LLMClient.from_env()
        reply = client.ping()
        print(f"  ✓  {client.model}  →  {reply}")
    except LLMError as e:
        print(f"  ✗  {e}", file=sys.stderr)
        sys.exit(1)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("llm", help="Exploratory LLM commands")
    g = p.add_subparsers(dest="action", required=True)

    g.add_parser("ping", help="Verify LLM connectivity and auth").set_defaults(
        func=cmd_ping
    )
