"""`nina tg bot|setup|dialogs|messages|send` — exploratory Telegram commands."""

import argparse
import sys

from nina.errors import TelegramError
from nina.integrations.telegram.client import TgClient


def cmd_bot(args: argparse.Namespace) -> None:  # noqa: ARG001
    from nina.integrations.telegram.bot import run_batch_from_env
    try:
        count = run_batch_from_env()
        print(f"Processed {count} command(s).")
    except TelegramError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_setup(args: argparse.Namespace) -> None:  # noqa: ARG001
    from nina.integrations.telegram.bot import setup_from_env
    try:
        setup_from_env()
    except TelegramError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_dialogs(args: argparse.Namespace) -> None:
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


def cmd_messages(args: argparse.Namespace) -> None:
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


def cmd_send(args: argparse.Namespace) -> None:
    try:
        with TgClient.from_env() as tg:
            tg.send_message(args.chat, args.text)
        print(f"Message sent to {args.chat}.")
    except TelegramError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("tg", help="Exploratory Telegram commands")
    g = p.add_subparsers(dest="action", required=True)

    g.add_parser(
        "bot", help="Process pending Telegram bot commands (batch mode)"
    ).set_defaults(func=cmd_bot)

    g.add_parser(
        "setup", help="Find your TELEGRAM_OWNER_ID (first-time setup)"
    ).set_defaults(func=cmd_setup)

    p_dialogs = g.add_parser(
        "dialogs", help="List recent Telegram chats/groups/channels"
    )
    p_dialogs.add_argument(
        "--limit", type=int, default=20, help="Maximum number of items to return"
    )
    p_dialogs.set_defaults(func=cmd_dialogs)

    p_messages = g.add_parser("messages", help="Show messages from a Telegram chat")
    p_messages.add_argument("chat", help="Chat id, username, or phone number")
    p_messages.add_argument(
        "--limit", type=int, default=20, help="Maximum number of items to return"
    )
    p_messages.set_defaults(func=cmd_messages)

    p_send = g.add_parser("send", help="Send a message to a Telegram chat")
    p_send.add_argument("chat", help="Chat id, username, or phone number")
    p_send.add_argument("text", help="Message text")
    p_send.set_defaults(func=cmd_send)
