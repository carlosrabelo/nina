"""`nina calendar list|events` — exploratory Google Calendar commands."""

import argparse
import sys

from nina.cli._env import tokens_dir
from nina.errors import AuthError, CalendarError
from nina.integrations.google.auth import discover_accounts
from nina.integrations.google.calendar.client import CalendarClient


def cmd_list(args: argparse.Namespace) -> None:
    td = tokens_dir()
    accounts = [args.account] if args.account else discover_accounts(td)

    if not accounts:
        print("No authenticated accounts found. Run: nina google auth")
        sys.exit(1)

    for account in accounts:
        try:
            calendars = CalendarClient(account, td).list_calendars()
        except (AuthError, CalendarError) as e:
            print(f"Error: {e}", file=sys.stderr)
            continue

        print(f"── {account} {'─' * (50 - len(account))}")
        for cal in calendars:
            marker = " (primary)" if cal.primary else ""
            print(f"  [{cal.access_role}]  {cal.name}{marker}")
            print(f"           id: {cal.id}")
        print()


def cmd_events(args: argparse.Namespace) -> None:
    td = tokens_dir()
    accounts = [args.account] if args.account else discover_accounts(td)

    if not accounts:
        print("No authenticated accounts found. Run: nina google auth")
        sys.exit(1)

    for account in accounts:
        try:
            events = CalendarClient(account, td).list_upcoming(
                args.limit, args.calendar
            )
        except (AuthError, CalendarError) as e:
            print(f"Error: {e}", file=sys.stderr)
            continue

        print(f"── {account} {'─' * (50 - len(account))}")
        if not events:
            print("  (no upcoming events)")
        for ev in events:
            print(f"  {ev.start}")
            print(f"  {ev.title}")
            if ev.location:
                print(f"  Local   : {ev.location}")
            print()


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("calendar", help="Exploratory Calendar commands")
    g = p.add_subparsers(dest="action", required=True)

    p_list = g.add_parser("list", help="List all calendars in the account")
    p_list.add_argument("--account", help="Filter to a specific account")
    p_list.set_defaults(func=cmd_list)

    p_events = g.add_parser("events", help="List upcoming Calendar events")
    p_events.add_argument("--account", help="Filter to a specific account")
    p_events.add_argument(
        "--calendar", default="primary", help="Calendar ID (default: primary)"
    )
    p_events.add_argument(
        "--limit", type=int, default=10, help="Maximum number of items to return"
    )
    p_events.set_defaults(func=cmd_events)
