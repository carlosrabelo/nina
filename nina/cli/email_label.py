"""`nina email process|infer-rules|rules` — Gmail label learning CLI."""

import argparse
import os
import sys
from pathlib import Path

from nina.errors import ConfigError


def cmd_list_rules(args: argparse.Namespace) -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el

    conn = open_db(data_dir)
    try:
        rules = el.list_rules(conn, account=args.account)
    finally:
        conn.close()

    if not rules:
        print("No learned rules in the database yet.")
        return

    for r in rules:
        arch = "archive" if r.archive_inbox else "keep-inbox"
        ts = r.created_at.isoformat(timespec="seconds") if r.created_at else ""
        print(f"{r.account}")
        print(f"  sender_norm : {r.sender_norm}")
        print(f"  label       : {r.label_name}")
        print(f"  inbox       : {arch}")
        print(f"  created_at  : {ts}")
        print()


def cmd_infer_rules(args: argparse.Namespace) -> None:
    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    try:
        from nina.tasks.email_infer_rules import run_infer_from_gmail_labels

        summary = run_infer_from_gmail_labels(
            tokens_dir,
            data_dir,
            max_per_account=args.max_per_account,
            since_days=args.days,
            min_agreeing_messages=args.min_messages,
            verbose=getattr(args, "verbose", False),
        )
    except ConfigError as e:
        print(f"Skipped: {e}", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(
        f"Infer-rules done.\n"
        f"  messages scanned: {summary.messages_scanned}\n"
        f"  rules added:      {summary.rules_added}\n"
        f"  skipped (existing rule): {summary.rules_skipped_existing}\n"
        f"  ambiguous (2+ user labels on a message): {summary.ambiguous_senders}"
    )


def cmd_process(args: argparse.Namespace) -> None:
    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    try:
        from nina.tasks.email_process import run_email_label_process

        run_email_label_process(
            tokens_dir,
            data_dir,
            bot_token=None,
            owner_id=None,
            send_telegram=False,
            verbose=args.verbose,
            days=args.days,
            max_per_account=args.max_per_account,
        )
    except ConfigError as e:
        print(f"Skipped: {e}", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print("Email process finished.")


def cmd_list_ignored(args: argparse.Namespace) -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    from nina.skills.email_label.execute import format_ignored_list

    print(format_ignored_list(data_dir, account=args.account))


def cmd_ignore_add(args: argparse.Namespace) -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    from nina.skills.email_label.execute import add_ignored

    print(add_ignored(data_dir, args.account, args.sender))


def cmd_ignore_remove(args: argparse.Namespace) -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    from nina.skills.email_label.execute import remove_ignored

    print(remove_ignored(data_dir, args.account, args.sender))


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("email", help="Gmail label learning (per account)")
    g = p.add_subparsers(dest="action", required=True)

    p_process = g.add_parser(
        "process",
        help=(
            "Fetch inbox messages, upsert email_messages, apply saved rules, "
            "optional Telegram suggestions (CLI: no Telegram)"
        ),
    )
    p_process.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=(
            "Progress on stderr (query, accounts, Gmail fetch, message batches)"
        ),
    )
    p_process.add_argument(
        "--days",
        type=int,
        default=None,
        metavar="D",
        help=(
            "Set or replace newer_than:Dd in NINA_EMAIL_SYNC_QUERY (backfill window)"
        ),
    )
    p_process.add_argument(
        "--max-per-account",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Max Gmail list results per account (default: env cap 500; CLI allows "
            "up to 5000)"
        ),
    )
    p_process.set_defaults(func=cmd_process)

    p_rules = g.add_parser(
        "rules",
        help="List learned sender→label rules stored in PostgreSQL (what Nina applies)",
    )
    p_rules.add_argument(
        "--account",
        help="Filter to one Gmail account email",
    )
    p_rules.set_defaults(func=cmd_list_rules)

    p_infer = g.add_parser(
        "infer-rules",
        help=(
            "Scan Gmail for user labels only to insert new sender→label rules "
            "(does not write email_messages or modify the inbox; use process for that)"
        ),
    )
    p_infer.add_argument(
        "--max-per-account",
        type=int,
        default=500,
        metavar="N",
        help="Max messages to fetch per Gmail account (default: 500)",
    )
    p_infer.add_argument(
        "--days",
        type=int,
        default=int(os.environ.get("NINA_EMAIL_LABEL_WINDOW_DAYS", "120")),
        metavar="D",
        help="Gmail newer_than:Dd window (default: 120)",
    )
    p_infer.add_argument(
        "--min-messages",
        type=int,
        default=int(os.environ.get("NINA_EMAIL_LABEL_MIN_HITS", "3")),
        metavar="M",
        help="Minimum messages with the same single user label (default: 3)",
    )
    p_infer.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Progress messages on stderr (accounts, Gmail fetch batches, DB writes)",
    )
    p_infer.set_defaults(func=cmd_infer_rules)

    p_ignore = g.add_parser(
        "ignore",
        help="Manage ignored senders (won't generate label suggestions)",
    )
    ig_sub = p_ignore.add_subparsers(dest="ignore_action", required=True)

    ig_list = ig_sub.add_parser(
        "list",
        help="List ignored senders",
    )
    ig_list.add_argument(
        "--account",
        help="Filter to one Gmail account email",
    )
    ig_list.set_defaults(func=cmd_list_ignored)

    ig_add = ig_sub.add_parser(
        "add",
        help="Add sender to ignored list",
    )
    ig_add.add_argument("account", help="Gmail account email")
    ig_add.add_argument("sender", help="Normalized sender email")
    ig_add.set_defaults(func=cmd_ignore_add)

    ig_remove = ig_sub.add_parser(
        "remove",
        help="Remove sender from ignored list",
    )
    ig_remove.add_argument("account", help="Gmail account email")
    ig_remove.add_argument("sender", help="Normalized sender email")
    ig_remove.set_defaults(func=cmd_ignore_remove)
