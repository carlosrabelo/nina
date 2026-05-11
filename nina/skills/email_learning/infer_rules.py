"""Infer sender → label rules from existing Gmail user labels on messages."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import NamedTuple

from nina.errors import ConfigError
from nina.integrations.google.gmail.client import GmailClient, GmailMultiClient
from nina.integrations.google.gmail.parse_sender import normalize_sender

log = logging.getLogger(__name__)


class InferSummary(NamedTuple):
    rules_added: int
    rules_skipped_existing: int
    messages_scanned: int
    ambiguous_senders: int


def _user_label_names_on_message(
    label_ids: list[str], user_id_to_name: dict[str, str]
) -> list[str]:
    names = [user_id_to_name[lid] for lid in label_ids if lid in user_id_to_name]
    return sorted(set(names))


def run_infer_from_gmail_labels(
    tokens_dir: Path,
    data_dir: Path,
    *,
    max_per_account: int = 500,
    since_days: int = 120,
    min_agreeing_messages: int = 2,
) -> InferSummary:
    """Scan recent mail per account; when one user-label dominates a sender, upsert a rule.

    Does not overwrite an existing rule for ``(account, sender_norm)``.
    """
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_learning as el
    from nina.core.store.repos.email_learning import SenderRule

    try:
        multi = GmailMultiClient.from_env()
    except ConfigError as e:
        log.info("email infer-rules skipped: %s", e)
        raise

    # (account, sender_norm) -> Counter(label_display_name)
    votes: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    scanned = 0
    ambiguous = 0

    query = f"newer_than:{since_days}d"

    for account in multi.accounts:
        gc = multi.client(account)
        user_map = gc.list_user_label_map()
        try:
            msgs = gc.search_paged(query, max_messages=max_per_account, page_size=100)
        except Exception as exc:
            log.warning("infer-rules: search failed %s: %s", account, exc)
            continue

        for msg in msgs:
            scanned += 1
            norm = normalize_sender(msg.sender)
            if not norm or "@" not in norm:
                continue
            names = _user_label_names_on_message(msg.labels, user_map)
            if not names:
                continue
            if len(names) > 1:
                ambiguous += 1
                continue
            votes[(account, norm)][names[0]] += 1

    conn = open_db(data_dir)
    added = 0
    skipped = 0
    try:
        for (account, norm), ctr in votes.items():
            if not ctr:
                continue
            label_name, count = ctr.most_common(1)[0]
            if count < min_agreeing_messages:
                continue
            if el.get_rule(conn, account, norm) is not None:
                skipped += 1
                continue
            el.upsert_rule(
                conn,
                SenderRule(
                    account=account,
                    sender_norm=norm,
                    label_name=label_name,
                    archive_inbox=True,
                ),
            )
            added += 1
    finally:
        conn.close()

    return InferSummary(
        rules_added=added,
        rules_skipped_existing=skipped,
        messages_scanned=scanned,
        ambiguous_senders=ambiguous,
    )
