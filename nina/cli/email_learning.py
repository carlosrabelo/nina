"""`nina email sync` — run Gmail learning sync once (no Telegram)."""

import argparse
import os
import sys
from pathlib import Path

from nina.errors import ConfigError


def cmd_infer_rules(args: argparse.Namespace) -> None:
    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    try:
        from nina.skills.email_learning.infer_rules import run_infer_from_gmail_labels

        summary = run_infer_from_gmail_labels(
            tokens_dir,
            data_dir,
            max_per_account=args.max_per_account,
            since_days=args.days,
            min_agreeing_messages=args.min_messages,
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


def cmd_sync(_args: argparse.Namespace) -> None:
    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    try:
        from nina.skills.email_learning.service import run_email_learning_sync

        run_email_learning_sync(
            tokens_dir, data_dir, bot_token=None, owner_id=None, send_telegram=False
        )
    except ConfigError as e:
        print(f"Skipped: {e}", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print("Email learning sync finished.")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("email", help="Gmail label learning (per account)")
    g = p.add_subparsers(dest="action", required=True)
    p_sync = g.add_parser(
        "sync",
        help="Ingest inbox + apply saved rules once (CLI only)",
    )
    p_sync.set_defaults(func=cmd_sync)

    p_infer = g.add_parser(
        "infer-rules",
        help=(
            "Scan recent mail on all accounts; if a sender already has one user "
            "label on enough messages, create a matching rule (does not overwrite "
            "existing rules)"
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
        default=120,
        metavar="D",
        help="Gmail newer_than:Dd window (default: 120)",
    )
    p_infer.add_argument(
        "--min-messages",
        type=int,
        default=2,
        metavar="M",
        help="Minimum messages with the same single user label (default: 2)",
    )
    p_infer.set_defaults(func=cmd_infer_rules)
