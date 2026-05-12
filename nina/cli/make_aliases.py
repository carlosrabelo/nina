"""Top-level commands mirroring historical `make` targets (`make cal-list`, etc.)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import nina
from nina.cli import auth as auth_mod
from nina.cli import calendar as cal_mod
from nina.cli import email_label as email_mod
from nina.cli import gmail as gmail_mod
from nina.cli import llm as llm_mod
from nina.cli import status as status_mod
from nina.cli import telegram as tg_mod


def _status_google(args: argparse.Namespace) -> None:  # noqa: ARG001
    status_mod.cmd_status(argparse.Namespace(provider="google"))


def _status_telegram(args: argparse.Namespace) -> None:  # noqa: ARG001
    status_mod.cmd_status(argparse.Namespace(provider="telegram"))


def _auth_google(args: argparse.Namespace) -> None:  # noqa: ARG001
    auth_mod.cmd_auth(argparse.Namespace(provider="google", phone=None))


def _auth_telegram(args: argparse.Namespace) -> None:
    auth_mod.cmd_auth(argparse.Namespace(provider="telegram", phone=args.phone))


def cmd_typecheck(args: argparse.Namespace) -> None:
    pkg = Path(nina.__file__).resolve().parent
    cmd: list[str] = [sys.executable, "-m", "mypy"]
    cmd.extend(args.paths if args.paths else [str(pkg)])
    raise SystemExit(subprocess.call(cmd))


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "auth-google",
        help="Google OAuth flow (alias: nina auth google)",
    )
    p.set_defaults(func=_auth_google)

    p = sub.add_parser(
        "auth-telegram",
        help="Authenticate Telegram (alias: nina auth telegram)",
    )
    p.add_argument("--phone", help="Phone number with country code")
    p.set_defaults(func=_auth_telegram)

    p = sub.add_parser(
        "status-google",
        help="Google auth status (alias: nina status google)",
    )
    p.set_defaults(func=_status_google)

    p = sub.add_parser(
        "status-telegram",
        help="Telegram auth status (alias: nina status telegram)",
    )
    p.set_defaults(func=_status_telegram)

    p = sub.add_parser(
        "cal-list",
        help="List calendars (alias: nina calendar list)",
    )
    p.add_argument("--account", help="Filter to a specific account")
    p.set_defaults(func=cal_mod.cmd_list)

    p = sub.add_parser(
        "cal-events",
        help="Upcoming events (alias: nina calendar events)",
    )
    p.add_argument("--account", help="Filter to a specific account")
    p.add_argument("--calendar", default="primary", help="Calendar ID")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cal_mod.cmd_events)

    p = sub.add_parser(
        "gmail-latest",
        help="Recent email headers (alias: nina gmail latest)",
    )
    p.add_argument("--account", help="Filter to a specific account")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=gmail_mod.cmd_latest)

    p = sub.add_parser(
        "gmail-unread",
        help="Unread messages (alias: nina gmail unread)",
    )
    p.add_argument("--account", help="Filter to a specific account")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=gmail_mod.cmd_unread)

    p = sub.add_parser(
        "gmail-search",
        help="Search Gmail (alias: nina gmail search QUERY)",
    )
    p.add_argument("query", help="Gmail search query")
    p.add_argument("--account", help="Filter to a specific account")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=gmail_mod.cmd_search)

    p = sub.add_parser(
        "gmail-labels",
        help="List Gmail labels (alias: nina gmail labels)",
    )
    p.add_argument("--account", help="Filter to a specific account")
    p.add_argument(
        "--user-only",
        action="store_true",
        help="Only user-created labels",
    )
    p.set_defaults(func=gmail_mod.cmd_labels)

    p = sub.add_parser(
        "email-process",
        help="Process inbox + rules once (alias: nina email process)",
    )
    p.add_argument("--days", type=int, default=None, metavar="D")
    p.add_argument("--max-per-account", type=int, default=None, metavar="N")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=email_mod.cmd_process)

    p = sub.add_parser(
        "email-infer-rules",
        help="Infer sender rules from Gmail labels (alias: nina email infer-rules)",
    )
    p.add_argument("--max-per-account", type=int, default=500, metavar="N")
    p.add_argument("--days", type=int, default=120, metavar="D")
    p.add_argument("--min-messages", type=int, default=2, metavar="M")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=email_mod.cmd_infer_rules)

    p = sub.add_parser(
        "email-rules",
        help="List learned sender→label rules (alias: nina email rules)",
    )
    p.add_argument("--account", help="Filter to one Gmail account email")
    p.set_defaults(func=email_mod.cmd_list_rules)

    p = sub.add_parser(
        "llm-ping",
        help="Verify LLM connectivity (alias: nina llm ping)",
    )
    p.set_defaults(func=llm_mod.cmd_ping)

    p = sub.add_parser(
        "tg-bot",
        help="Batch Telegram bot commands (alias: nina tg bot)",
    )
    p.set_defaults(func=tg_mod.cmd_bot)

    p = sub.add_parser(
        "tg-setup",
        help="Discover TELEGRAM_OWNER_ID (alias: nina tg setup)",
    )
    p.set_defaults(func=tg_mod.cmd_setup)

    p = sub.add_parser(
        "tg-dialogs",
        help="List Telegram dialogs (alias: nina tg dialogs)",
    )
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=tg_mod.cmd_dialogs)

    p = sub.add_parser(
        "tg-messages",
        help="Messages from a chat (alias: nina tg messages CHAT)",
    )
    p.add_argument("chat", help="Chat id, username, or phone")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=tg_mod.cmd_messages)

    p = sub.add_parser(
        "tg-send",
        help="Send Telegram message (alias: nina tg send CHAT TEXT)",
    )
    p.add_argument("chat", help="Chat id, username, or phone")
    p.add_argument("text", help="Message text")
    p.set_defaults(func=tg_mod.cmd_send)

    p = sub.add_parser(
        "typecheck",
        help="Run mypy on the nina package",
    )
    p.add_argument(
        "paths",
        nargs="*",
        help="Paths for mypy (default: installed nina package)",
    )
    p.set_defaults(func=cmd_typecheck)
