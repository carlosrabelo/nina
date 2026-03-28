"""Nina Play — experimental commands and exploration."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from nina.errors import AuthError, CalendarError, ConfigError, GmailError, LLMError, TelegramError
from nina.google.auth import discover_accounts
from nina.google.calendar.client import CalendarClient
from nina.google.gmail.client import GmailMultiClient
from nina.llm.client import LLMClient
from nina.telegram.client import TgClient


def _tokens_dir() -> Path:
    load_dotenv()
    return Path(os.environ.get("TOKENS_DIR", "tokens"))


# ── Calendar ──────────────────────────────────────────────────────────────────

def cmd_calendars(args: argparse.Namespace) -> None:
    """List all calendars in one or all accounts."""
    tokens_dir = _tokens_dir()
    accounts = [args.account] if args.account else discover_accounts(tokens_dir)

    if not accounts:
        print("No authenticated accounts found. Run: nina auth")
        sys.exit(1)

    for account in accounts:
        try:
            calendars = CalendarClient(account, tokens_dir).list_calendars()
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
    """List upcoming Calendar events for one or all accounts."""
    tokens_dir = _tokens_dir()
    accounts = [args.account] if args.account else discover_accounts(tokens_dir)

    if not accounts:
        print("No authenticated accounts found. Run: nina auth")
        sys.exit(1)

    for account in accounts:
        try:
            events = CalendarClient(account, tokens_dir).list_upcoming(
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


# ── Gmail ─────────────────────────────────────────────────────────────────────

def cmd_latest(args: argparse.Namespace) -> None:
    """Show headers of the most recent emails from one or all accounts."""
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
    """List unread messages."""
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
    """Search messages with Gmail query syntax."""
    try:
        client = GmailMultiClient.from_env()
        messages = client.search(args.query, account=args.account, max_results=args.limit)
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


# ── LLM ───────────────────────────────────────────────────────────────────────

def cmd_llm_ping(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Verify LLM connectivity and authentication."""
    try:
        client = LLMClient.from_env()
        reply = client.ping()
        print(f"  ✓  {client.model}  →  {reply}")
    except LLMError as e:
        print(f"  ✗  {e}", file=sys.stderr)
        sys.exit(1)


# ── Telegram ──────────────────────────────────────────────────────────────────

def cmd_tg_bot(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Process pending Telegram bot commands (batch mode — fetches and exits)."""
    from nina.telegram.bot import run_batch_from_env
    try:
        count = run_batch_from_env()
        print(f"Processed {count} command(s).")
    except TelegramError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_tg_bot_setup(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Discover who messaged the bot and print their chat IDs."""
    from nina.telegram.bot import setup_from_env
    try:
        setup_from_env()
    except TelegramError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_tg_dialogs(args: argparse.Namespace) -> None:
    """List recent Telegram chats/groups/channels."""
    try:
        with TgClient.from_env() as tg:
            dialogs = tg.list_dialogs(args.limit)
    except TelegramError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    for d in dialogs:
        unread = f" [{d.unread_count} unread]" if d.unread_count else ""
        print(f"  ({d.kind})  {d.name}{unread}")
        print(f"             id: {d.id}")


def cmd_tg_messages(args: argparse.Namespace) -> None:
    """Show messages from a Telegram chat."""
    try:
        with TgClient.from_env() as tg:
            messages = tg.get_messages(args.chat, args.limit)
    except TelegramError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not messages:
        print("No messages found.")
        return

    for msg in messages:
        direction = "→" if msg.is_outgoing else "←"
        print(f"  {direction}  [{msg.date}]  {msg.sender}")
        print(f"     {msg.text[:120]}")
        print()


def cmd_tg_send(args: argparse.Namespace) -> None:
    """Send a message to a Telegram chat."""
    try:
        with TgClient.from_env() as tg:
            tg.send_message(args.chat, args.text)
        print(f"Message sent to {args.chat}.")
    except TelegramError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


# ── Parser ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="nina-play",
        description="Nina Play — experimental commands and exploration",
    )
    sub = parser.add_subparsers(dest="command")

    # Calendar
    p_calendars = sub.add_parser("calendars", help="List all calendars in the account")
    p_calendars.add_argument("--account", help="Filter to a specific account")
    p_calendars.set_defaults(func=cmd_calendars)

    p_events = sub.add_parser("events", help="List upcoming Calendar events")
    p_events.add_argument("--account", help="Filter to a specific account")
    p_events.add_argument("--calendar", default="primary", help="Calendar ID (default: primary)")
    p_events.add_argument("--limit", type=int, default=10)
    p_events.set_defaults(func=cmd_events)

    # Gmail
    p_latest = sub.add_parser("latest", help="Show headers of the most recent emails")
    p_latest.add_argument("--account", help="Filter to a specific account")
    p_latest.add_argument("--limit", type=int, default=10)
    p_latest.set_defaults(func=cmd_latest)

    p_unread = sub.add_parser("unread", help="List unread messages")
    p_unread.add_argument("--account", help="Filter to a specific account")
    p_unread.add_argument("--limit", type=int, default=20)
    p_unread.set_defaults(func=cmd_unread)

    p_search = sub.add_parser("search", help="Search messages (Gmail query syntax)")
    p_search.add_argument("query")
    p_search.add_argument("--account", help="Filter to a specific account")
    p_search.add_argument("--limit", type=int, default=20)
    p_search.set_defaults(func=cmd_search)

    # LLM
    p_llm_ping = sub.add_parser("llm-ping", help="Verify LLM connectivity and auth")
    p_llm_ping.set_defaults(func=cmd_llm_ping)

    # Telegram
    p_tg_bot = sub.add_parser("tg-bot", help="Process pending Telegram bot commands (batch mode)")
    p_tg_bot.set_defaults(func=cmd_tg_bot)

    p_tg_setup = sub.add_parser("tg-bot-setup", help="Find your TELEGRAM_OWNER_ID")
    p_tg_setup.set_defaults(func=cmd_tg_bot_setup)

    p_tg_dialogs = sub.add_parser("tg-dialogs", help="List recent Telegram chats/groups/channels")
    p_tg_dialogs.add_argument("--limit", type=int, default=20)
    p_tg_dialogs.set_defaults(func=cmd_tg_dialogs)

    p_tg_messages = sub.add_parser("tg-messages", help="Show messages from a Telegram chat")
    p_tg_messages.add_argument("chat", help="Chat id, username, or phone number")
    p_tg_messages.add_argument("--limit", type=int, default=20)
    p_tg_messages.set_defaults(func=cmd_tg_messages)

    p_tg_send = sub.add_parser("tg-send", help="Send a message to a Telegram chat")
    p_tg_send.add_argument("chat", help="Chat id, username, or phone number")
    p_tg_send.add_argument("text", help="Message text")
    p_tg_send.set_defaults(func=cmd_tg_send)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)
