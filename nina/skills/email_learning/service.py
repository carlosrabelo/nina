"""Ingest inbox headers, apply per-account learned labels, notify on new senders."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

log = logging.getLogger(__name__)


def _min_hits() -> int:
    return max(1, int(os.environ.get("NINA_EMAIL_LABEL_MIN_HITS", "3")))


def _max_messages() -> int:
    return max(1, min(500, int(os.environ.get("NINA_EMAIL_SYNC_MAX_MESSAGES", "80"))))


def _inbox_query() -> str:
    return os.environ.get("NINA_EMAIL_SYNC_QUERY", "in:inbox newer_than:14d").strip()


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
    from nina.core.store.repos import email_learning as el

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
            "emailtag.suggest_telegram",
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


def run_email_learning_process(
    tokens_dir: Path,
    data_dir: Path,
    *,
    bot_token: str | None = None,
    owner_id: int | None = None,
    send_telegram: bool = True,
) -> None:
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_learning as el
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
    max_list = _max_messages()
    query = _inbox_query()

    try:
        if send_telegram and bot_token and owner_id is not None:
            flush_pending_telegram(conn, data_dir, bot_token, owner_id)

        for account in multi.accounts:
            gc = multi.client(account)
            try:
                msgs = gc.search(query, max_results=max_list)
            except Exception as exc:
                log.warning("email learning: list failed %s: %s", account, exc)
                continue

            for msg in msgs:
                norm = normalize_sender(msg.sender)
                if not norm or "@" not in norm:
                    continue

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

                cnt = el.count_sender_in_window(conn, account, norm, days=30)
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
                            "emailtag.suggest_telegram",
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
    finally:
        conn.close()


def teach_label_for_pending(
    tokens_dir: Path,
    data_dir: Path,
    id_prefix: str,
    label_name: str,
    *,
    archive_inbox: bool = True,
) -> str:
    """Save rule by pending id prefix, then label matching messages."""
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_learning as el
    from nina.core.store.repos.email_learning import SenderRule
    from nina.integrations.google.gmail.client import GmailMultiClient

    _ = tokens_dir  # reserved for future account-specific token roots
    lang = load_locale(data_dir).lang
    id_prefix = id_prefix.strip()
    if len(id_prefix) < 8:
        return t("emailtag.id_too_short", lang)
    label_name = label_name.strip()
    if not label_name:
        return t("emailtag.label_empty", lang)

    conn = open_db(data_dir)
    try:
        try:
            pending = el.get_pending_by_id_prefix(conn, id_prefix)
        except ValueError:
            return t("emailtag.ambiguous_id", lang)

        if pending is None:
            return t("emailtag.pending_not_found", lang)

        rule = SenderRule(
            account=pending.account,
            sender_norm=pending.sender_norm,
            label_name=label_name,
            archive_inbox=archive_inbox,
        )
        el.upsert_rule(conn, rule)
        el.close_pending_taught(conn, pending.id)

        multi = GmailMultiClient.from_env()
        gc = multi.client(pending.account)
        lid = gc.ensure_user_label(label_name)
        mids = el.list_untagged_for_sender(
            conn, pending.account, pending.sender_norm, limit=100
        )
        applied_ids: list[str] = []
        for mid in mids:
            try:
                gc.apply_label(mid, lid, archive_inbox=archive_inbox)
                applied_ids.append(mid)
            except Exception:
                continue
        if applied_ids:
            el.mark_messages_tagged(
                conn, pending.account, applied_ids, label_name
            )

        return t(
            "emailtag.taught_ok",
            lang,
            sender=pending.sender_norm,
            label=label_name,
            account=pending.account,
            applied=len(applied_ids),
        )
    finally:
        conn.close()


def dismiss_pending_by_prefix(data_dir: Path, id_prefix: str) -> str:
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_learning as el

    lang = load_locale(data_dir).lang
    id_prefix = id_prefix.strip()
    if len(id_prefix) < 8:
        return t("emailtag.id_too_short", lang)
    conn = open_db(data_dir)
    try:
        try:
            pending = el.get_pending_by_id_prefix(conn, id_prefix)
        except ValueError:
            return t("emailtag.ambiguous_id", lang)
        if pending is None:
            return t("emailtag.pending_not_found", lang)
        if not el.dismiss_pending(conn, pending.id):
            return t("emailtag.pending_not_found", lang)
        return t("emailtag.dismiss_ok", lang, sender=pending.sender_norm)
    finally:
        conn.close()


def format_pending_list(data_dir: Path) -> str:
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_learning as el

    lang = load_locale(data_dir).lang
    conn = open_db(data_dir)
    try:
        rows = el.list_open_pending(conn)
        if not rows:
            return t("emailtag.no_pending", lang)
        lines = [t("emailtag.pending_header", lang)]
        for p in rows:
            lines.append(
                t(
                    "emailtag.pending_line",
                    lang,
                    short_id=p.id[:12],
                    full_id=p.id,
                    account=p.account,
                    sender=p.sender_norm,
                    hits=p.hit_count,
                    subject=(p.sample_subject or "")[:80],
                )
            )
        return "\n".join(lines)
    finally:
        conn.close()
