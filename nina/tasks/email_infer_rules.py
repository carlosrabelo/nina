"""Infer sender → label rules from existing Gmail user labels on messages."""

from __future__ import annotations

import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import NamedTuple

from nina.errors import ConfigError
from nina.integrations.google.gmail.client import GmailMultiClient
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
    names = [
        user_id_to_name[lid]
        for lid in label_ids
        if lid in user_id_to_name and user_id_to_name[lid].startswith(("@", "!"))
    ]
    return sorted(set(names))


def _verbose_print(enabled: bool, msg: str) -> None:
    if enabled:
        print(msg, file=sys.stderr, flush=True)


def run_infer_from_gmail_labels(
    tokens_dir: Path,
    data_dir: Path,
    *,
    account: str | None = None,
    max_per_account: int = 500,
    since_days: int = 120,
    min_agreeing_messages: int = 3,
    verbose: bool = False,
) -> InferSummary:
    """Scan recent Gmail only to infer new rows in ``email_sender_rules``.

    Does **not** write ``email_messages`` or touch the inbox — use
    ``nina email process`` for that. When one user-label dominates a sender across
    scanned messages, inserts a rule (does not overwrite an existing rule for
    ``(account, sender_norm)``).
    """
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el
    from nina.core.store.repos.email_label import SenderRule

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

    _verbose_print(
        verbose,
        "[infer-rules] "
        f"query={query!r} max_per_account={max_per_account} "
        f"min_agreeing_messages={min_agreeing_messages}",
    )
    _verbose_print(
        verbose,
        f"[infer-rules] Gmail accounts ({len(multi.accounts)}): {', '.join(multi.accounts)}",
    )

    for acct in multi.accounts:
        if account and acct != account:
            continue
        gc = multi.client(acct)
        _verbose_print(verbose, f"[infer-rules] {acct} — loading user label map…")
        user_map = gc.list_user_label_map()
        _verbose_print(
            verbose,
            f"[infer-rules] {acct} — {len(user_map)} user labels; "
            "searching messages (metadata fetch per message, can take a while)…",
        )

        def _on_batch(n: int, acc: str = acct) -> None:
            _verbose_print(
                verbose,
                f"[infer-rules] {acc} — fetched {n}/{max_per_account} messages…",
            )

        try:
            msgs = gc.search_paged(
                query,
                max_messages=max_per_account,
                page_size=100,
                on_batch=_on_batch if verbose else None,
            )
        except Exception as exc:
            log.warning("infer-rules: search failed %s: %s", acct, exc)
            _verbose_print(verbose, f"[infer-rules] {acct} — search failed: {exc}")
            continue

        _verbose_print(
            verbose, f"[infer-rules] {acct} — scan done, {len(msgs)} messages"
        )

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
            votes[(acct, norm)][names[0]] += 1

    _verbose_print(
        verbose,
        f"[infer-rules] vote keys (account, sender): {len(votes)} — writing rules to DB…",
    )
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
            if verbose and added % 20 == 0:
                _verbose_print(verbose, f"[infer-rules] … {added} new rules committed")
    finally:
        conn.close()

    return InferSummary(
        rules_added=added,
        rules_skipped_existing=skipped,
        messages_scanned=scanned,
        ambiguous_senders=ambiguous,
    )
