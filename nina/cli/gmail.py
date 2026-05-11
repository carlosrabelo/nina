"""`nina gmail latest|unread|search|labels` — exploratory Gmail commands."""

import argparse
import sys

from nina.errors import AuthError, ConfigError, GmailError
from nina.integrations.google.gmail.client import GmailMultiClient


def cmd_latest(args: argparse.Namespace) -> None:
    try:
        client = GmailMultiClient.from_env()
        accounts = [args.account] if args.account else client.accounts
        for account in accounts:
            messages = client.client(account).list_latest(max_results=args.limit)
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
    try:
        client = GmailMultiClient.from_env()
        messages = client.list_unread(account=args.account, max_results=args.limit)
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
    try:
        client = GmailMultiClient.from_env()
        messages = client.search(
            args.query, account=args.account, max_results=args.limit
        )
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


def cmd_labels(args: argparse.Namespace) -> None:
    try:
        client = GmailMultiClient.from_env()
        accounts = [args.account] if args.account else client.accounts
        for account in accounts:
            labels = client.client(account).list_labels()
            if args.user_only:
                labels = [lb for lb in labels if lb.label_type == "user"]
            print(f"── {account} ({len(labels)} labels)")
            rows = sorted(labels, key=lambda lb: (lb.label_type, lb.name.lower()))
            for lb in rows:
                print(f"  {lb.label_type:8}  {lb.id:22}  {lb.name}")
            print()
    except (ConfigError, AuthError, GmailError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("gmail", help="Exploratory Gmail commands")
    g = p.add_subparsers(dest="action", required=True)

    p_latest = g.add_parser("latest", help="Show headers of the most recent emails")
    p_latest.add_argument("--account", help="Filter to a specific account")
    p_latest.add_argument("--limit", type=int, default=10)
    p_latest.set_defaults(func=cmd_latest)

    p_unread = g.add_parser("unread", help="List unread messages")
    p_unread.add_argument("--account", help="Filter to a specific account")
    p_unread.add_argument("--limit", type=int, default=20)
    p_unread.set_defaults(func=cmd_unread)

    p_search = g.add_parser("search", help="Search messages (Gmail query syntax)")
    p_search.add_argument("query")
    p_search.add_argument("--account", help="Filter to a specific account")
    p_search.add_argument("--limit", type=int, default=20)
    p_search.set_defaults(func=cmd_search)

    p_labels = g.add_parser(
        "labels",
        help="List Gmail labels (system + user; use --user-only for your tags only)",
    )
    p_labels.add_argument("--account", help="Filter to a specific account")
    p_labels.add_argument(
        "--user-only",
        action="store_true",
        help="Show only user-created labels (typical “tags” for learning rules)",
    )
    p_labels.set_defaults(func=cmd_labels)
