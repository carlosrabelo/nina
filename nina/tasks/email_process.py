"""Ingest inbox headers, apply per-account learned labels, notify on new senders."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

log = logging.getLogger(__name__)

_NEWER_THAN_RE = re.compile(r"\bnewer_than:\s*\d+\s*d\b", re.IGNORECASE)


def _verbose_print(enabled: bool, msg: str) -> None:
    if enabled:
        print(msg, file=sys.stderr, flush=True)


def _min_hits() -> int:
    return max(1, int(os.environ.get("NINA_EMAIL_LABEL_MIN_HITS", "3")))


def _window_days() -> int:
    return max(1, int(os.environ.get("NINA_EMAIL_LABEL_WINDOW_DAYS", "120")))


def _max_messages() -> int:
    return max(1, min(500, int(os.environ.get("NINA_EMAIL_SYNC_MAX_MESSAGES", "80"))))


def _inbox_query() -> str:
    return os.environ.get("NINA_EMAIL_SYNC_QUERY", "in:inbox newer_than:14d").strip()


def _process_gmail_query(days: int | None) -> str:
    """Effective Gmail search query: env base, optional ``newer_than`` override."""
    base = _inbox_query()
    if days is None:
        return base
    d = max(1, int(days))
    token = f"newer_than:{d}d"
    if _NEWER_THAN_RE.search(base):
        return _NEWER_THAN_RE.sub(token, base, count=1)
    return f"{base} {token}".strip()


def _process_max_messages(max_per_account: int | None) -> int:
    """Env default caps at 500; explicit CLI ``max_per_account`` allows up to 5000."""
    if max_per_account is not None:
        return max(1, min(5000, int(max_per_account)))
    return _max_messages()


def _send_telegram(bot_token: str, owner_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = json.dumps(
        {"chat_id": owner_id, "text": text[:4000]}
    ).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=15)
    except urllib.error.URLError as e:
        log.warning("email learning telegram send failed: %s", e)


def _may_notify_telegram(data_dir: Path) -> bool:
    """Respect DND and work/lunch window (same spirit as calendar notifications)."""
    from nina.skills.presence.models import PresenceStatus
    from nina.skills.presence.store import load as load_presence
    from nina.skills.workdays.checker import get_context
    from nina.skills.workdays.store import load as load_workdays

    presence = load_presence(data_dir)
    if presence.status == PresenceStatus.DND:
        return False
    ctx = get_context(load_workdays(data_dir), presence, "en")
    return bool(ctx.is_work_time or ctx.is_lunch_time)


def flush_pending_telegram(
    conn,
    data_dir: Path,
    bot_token: str,
    owner_id: int,
) -> None:
    """Send Telegram for pending rows not yet notified (e.g. created off-hours)."""
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.repos import email_label as el

    if not _may_notify_telegram(data_dir):
        return

    lang = load_locale(data_dir).lang
    rows = conn.execute(
        """
        SELECT id, account, sender_norm, sample_subject, hit_count
        FROM email_pending_labels
        WHERE status = 'open' AND notified = false
        ORDER BY created_at ASC
        LIMIT 20
        """
    ).fetchall()
    for row in rows:
        text = t(
            "gmail_label.suggest_telegram",
            lang,
            account=row["account"],
            sender=row["sender_norm"],
            subject=(row.get("sample_subject") or "")[:200],
            count=row["hit_count"],
            full_id=row["id"],
            short_id=row["id"][:12],
        )
        _send_telegram(bot_token, owner_id, text)
        el.set_pending_notified(conn, row["id"])


def run_email_label_process(
    tokens_dir: Path,
    data_dir: Path,
    *,
    bot_token: str | None = None,
    owner_id: int | None = None,
    send_telegram: bool = True,
    verbose: bool = False,
    days: int | None = None,
    max_per_account: int | None = None,
) -> None:
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el
    from nina.errors import ConfigError
    from nina.integrations.google.gmail.client import GmailMultiClient
    from nina.integrations.google.gmail.parse_sender import normalize_sender

    try:
        multi = GmailMultiClient.from_env()
    except ConfigError as e:
        log.info("email learning process skipped: %s", e)
        return

    conn = open_db(data_dir)
    min_hits = _min_hits()
    max_list = _process_max_messages(max_per_account)
    query = _process_gmail_query(days)
    _verbose_print(
        verbose,
        f"[email process] query={query!r} max_messages={max_list} "
        f"min_hits_for_pending={min_hits} telegram={send_telegram}",
    )
    _verbose_print(verbose, f"[email process] accounts: {', '.join(multi.accounts)}")

    try:
        if send_telegram and bot_token and owner_id is not None:
            flush_pending_telegram(conn, data_dir, bot_token, owner_id)
            _verbose_print(verbose, "[email process] flush_pending_telegram done")
        elif verbose:
            _verbose_print(
                verbose,
                "[email process] Telegram flush skipped "
                "(no bot context or send_telegram=false)",
            )

        for account in multi.accounts:
            gc = multi.client(account)
            try:
                msgs = gc.search(query, max_results=max_list)
            except Exception as exc:
                log.warning("email learning: list failed %s: %s", account, exc)
                _verbose_print(
                    verbose,
                    f"[email process] {account} — search failed: {exc}",
                )
                continue

            _verbose_print(
                verbose,
                f"[email process] {account} — fetched {len(msgs)} messages",
            )
            n_valid = 0
            for msg in msgs:
                if el.is_message_tagged(conn, account, msg.id):
                    continue

                norm = normalize_sender(msg.sender)
                if not norm or "@" not in norm:
                    continue

                n_valid += 1
                if verbose and n_valid % 20 == 0:
                    _verbose_print(
                        verbose,
                        f"[email process] {account} … {n_valid} valid-sender messages",
                    )

                el.upsert_seen_message(
                    conn,
                    account,
                    msg.id,
                    msg.thread_id,
                    msg.sender,
                    norm,
                    msg.subject,
                    msg.date or "",
                )

                rule = el.get_rule(conn, account, norm)
                if rule:
                    if not el.is_message_tagged(conn, account, msg.id):
                        try:
                            lid = gc.ensure_user_label(rule.label_name)
                            gc.apply_label(
                                msg.id, lid, archive_inbox=rule.archive_inbox
                            )
                            el.mark_messages_tagged(
                                conn, account, [msg.id], rule.label_name
                            )
                        except Exception as exc:
                            log.warning(
                                "email learning: apply label %s %s: %s",
                                account,
                                msg.id,
                                exc,
                            )
                    continue

                if el.is_sender_ignored(conn, account, norm):
                    continue

                cnt = el.count_sender_in_window(conn, account, norm, days=_window_days())
                existing = el.find_open_pending(conn, account, norm)
                if existing:
                    el.update_pending_hit(
                        conn,
                        existing.id,
                        cnt,
                        (msg.subject or "")[:500],
                    )
                    continue

                if cnt < min_hits:
                    continue

                pid = uuid.uuid4().hex
                el.insert_pending(
                    conn,
                    pid,
                    account,
                    norm,
                    msg.sender,
                    (msg.subject or "")[:500],
                    cnt,
                )

                if send_telegram and bot_token and owner_id is not None:
                    if _may_notify_telegram(data_dir):
                        from nina.core.i18n import t
                        from nina.core.locale.store import load as load_locale

                        lang = load_locale(data_dir).lang
                        text = t(
                            "gmail_label.suggest_telegram",
                            lang,
                            account=account,
                            sender=norm,
                            subject=(msg.subject or "")[:200],
                            count=cnt,
                            full_id=pid,
                            short_id=pid[:12],
                        )
                        _send_telegram(bot_token, owner_id, text)
                        el.set_pending_notified(conn, pid)
            _verbose_print(
                verbose,
                f"[email process] {account} — done",
            )
        _verbose_print(verbose, "[email process] all accounts finished")
    finally:
        conn.close()


