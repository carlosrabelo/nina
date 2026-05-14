"""`nina gmail_label process|infer-rules|rules` — Gmail label learning CLI."""

import argparse
import os
import sys
from pathlib import Path

from nina.errors import ConfigError


def cmd_rule_add(args: argparse.Namespace) -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    from nina.skills.gmail_label.execute import add_rule_direct

    print(add_rule_direct(data_dir, args.account, args.sender, args.label))


def cmd_rules_check(args: argparse.Namespace) -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    from nina.skills.gmail_label.execute import check_rules

    print(check_rules(data_dir, tokens_dir, account=args.account))


def cmd_pending_scan(args: argparse.Namespace) -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    from nina.skills.gmail_label.execute import scan_pending_suggestions

    print(scan_pending_suggestions(
        data_dir,
        min_hits=args.min_messages,
        window_days=args.days,
        account=args.account,
        verbose=args.verbose,
    ))


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
            account=args.account,
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
            account=args.account,
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
    from nina.skills.gmail_label.execute import format_ignored_list

    print(format_ignored_list(data_dir, account=args.account))


def cmd_ignore_add(args: argparse.Namespace) -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    from nina.skills.gmail_label.execute import add_ignored

    print(add_ignored(data_dir, args.account, args.sender))


def cmd_ignore_remove(args: argparse.Namespace) -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    from nina.skills.gmail_label.execute import remove_ignored

    print(remove_ignored(data_dir, args.account, args.sender))


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("gmail_label", help="Gmail label learning (per account)")
    g = p.add_subparsers(dest="action", required=True)

    p_process = g.add_parser(
        "process",
        help=(
            "Fetch inbox messages, upsert email_messages, apply saved rules"
        ),
    )
    p_process.add_argument(
        "--account",
        default=None,
        help="Filter to a specific account",
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
        metavar="DAYS",
        help="Look back DAYS days in email_messages (backfill window)",
    )
    p_process.add_argument(
        "--max-per-account",
        type=int,
        default=None,
        metavar="NUM",
        help=(
            "Max Gmail list results per account (default: env cap 500; CLI allows "
            "up to 5000)"
        ),
    )
    p_process.set_defaults(func=cmd_process)

    p_rules = g.add_parser(
        "rules",
        help="Manage learned sender→label rules",
    )
    rules_sub = p_rules.add_subparsers(dest="rules_action", required=True)

    rules_list = rules_sub.add_parser(
        "list",
        help="List learned sender→label rules stored in PostgreSQL",
    )
    rules_list.add_argument(
        "--account",
        help="Filter to a specific account",
    )
    rules_list.set_defaults(func=cmd_list_rules)

    rules_check = rules_sub.add_parser(
        "check",
        help="Validate rules (prefix, Gmail label existence, tokens, ignored conflicts)",
    )
    rules_check.add_argument(
        "--account",
        help="Filter to a specific account",
    )
    rules_check.set_defaults(func=cmd_rules_check)

    p_infer = g.add_parser(
        "infer-rules",
        help=(
            "Scan Gmail for user labels only to insert new sender→label rules "
            "(does not write email_messages or modify the inbox; use process for that)"
        ),
    )
    p_infer.add_argument(
        "--account",
        help="Filter to a specific Gmail account",
    )
    p_infer.add_argument(
        "--max-per-account",
        type=int,
        default=500,
        metavar="NUM",
        help="Max messages to fetch per Gmail account (default: 500)",
    )
    p_infer.add_argument(
        "--days",
        type=int,
        default=int(os.environ.get("NINA_EMAIL_LABEL_WINDOW_DAYS", "120")),
        metavar="DAYS",
        help="Look back DAYS days in email_messages (default: 120)",
    )
    p_infer.add_argument(
        "--min-messages",
        type=int,
        default=int(os.environ.get("NINA_EMAIL_LABEL_MIN_HITS", "3")),
        metavar="NUM",
        help="Minimum messages with the same single user label (default: 3)",
    )
    p_infer.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Progress messages on stderr (accounts, Gmail fetch batches, DB writes)",
    )
    p_infer.set_defaults(func=cmd_infer_rules)

    p_pending = g.add_parser(
        "pending",
        help="Manage pending sender suggestions",
    )
    pending_sub = p_pending.add_subparsers(dest="pending_action", required=True)

    pending_scan = pending_sub.add_parser(
        "scan",
        help="Scan email_messages for new sender candidates and create pending suggestions",
    )
    pending_scan.add_argument(
        "--account",
        default=None,
        help="Filter to a specific account",
    )
    pending_scan.add_argument(
        "--days",
        type=int,
        default=None,
        metavar="DAYS",
        help="Look back DAYS days in email_messages (default: env NINA_EMAIL_LABEL_WINDOW_DAYS or 120)",
    )
    pending_scan.add_argument(
        "--min-messages",
        type=int,
        default=None,
        metavar="NUM",
        help="Minimum untagged messages to consider a candidate (default: env NINA_EMAIL_LABEL_MIN_HITS or 3)",
    )
    pending_scan.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print each candidate created on stderr",
    )
    pending_scan.set_defaults(func=cmd_pending_scan)

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
        help="Filter to a specific account",
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

    p_rule = g.add_parser(
        "rule",
        help="Manage sender rules directly",
    )
    rule_sub = p_rule.add_subparsers(dest="rule_action", required=True)

    rule_add = rule_sub.add_parser(
        "add",
        help="Add a sender rule manually",
    )
    rule_add.add_argument("account", help="Gmail account email")
    rule_add.add_argument("sender", help="Sender email address")
    rule_add.add_argument("label", help="Gmail label (must start with @ or !)")
    rule_add.set_defaults(func=cmd_rule_add)
