from pathlib import Path


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
    from nina.core.store.repos import email_label as el
    from nina.core.store.repos.email_label import SenderRule
    from nina.integrations.google.gmail.client import GmailMultiClient

    _ = tokens_dir  # reserved for future account-specific token roots
    lang = load_locale(data_dir).lang
    id_prefix = id_prefix.strip()
    if len(id_prefix) < 8:
        return t("email_label.id_too_short", lang)
    label_name = label_name.strip()
    if not label_name:
        return t("email_label.label_empty", lang)
    if not label_name.startswith("@"):
        return t("email_label.label_must_at", lang)

    conn = open_db(data_dir)
    try:
        try:
            pending = el.get_pending_by_id_prefix(conn, id_prefix)
        except ValueError:
            return t("email_label.ambiguous_id", lang)

        if pending is None:
            return t("email_label.pending_not_found", lang)

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
            "email_label.taught_ok",
            lang,
            sender=pending.sender_norm,
            label=label_name,
            account=pending.account,
            applied=len(applied_ids),
        )
    finally:
        conn.close()


def dismiss_all_pending_labels(data_dir: Path) -> str:
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el

    lang = load_locale(data_dir).lang
    conn = open_db(data_dir)
    try:
        count = el.dismiss_all_pending(conn)
        return t("email_label.dismiss_all_ok", lang, count=count)
    finally:
        conn.close()


def dismiss_pending_by_prefix(data_dir: Path, id_prefix: str) -> str:
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el

    lang = load_locale(data_dir).lang
    id_prefix = id_prefix.strip()
    if len(id_prefix) < 8:
        return t("email_label.id_too_short", lang)
    conn = open_db(data_dir)
    try:
        try:
            pending = el.get_pending_by_id_prefix(conn, id_prefix)
        except ValueError:
            return t("email_label.ambiguous_id", lang)
        if pending is None:
            return t("email_label.pending_not_found", lang)
        if not el.dismiss_pending(conn, pending.id):
            return t("email_label.pending_not_found", lang)
        el.add_ignored_sender(conn, pending.account, pending.sender_norm)
        return t("email_label.dismiss_ok", lang, sender=pending.sender_norm)
    finally:
        conn.close()


def format_pending_list(data_dir: Path) -> str:
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el

    lang = load_locale(data_dir).lang
    conn = open_db(data_dir)
    try:
        rows = el.list_open_pending(conn)
        if not rows:
            return t("email_label.no_pending", lang)
        lines = [t("email_label.pending_header", lang)]
        for p in rows:
            lines.append(
                t(
                    "email_label.pending_line",
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


def format_ignored_list(data_dir: Path, *, account: str | None = None) -> str:
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el

    lang = load_locale(data_dir).lang
    conn = open_db(data_dir)
    try:
        rows = el.list_ignored_senders(conn, account=account)
        if not rows:
            return t("email_label.ignore_empty", lang)
        lines = [t("email_label.ignore_header", lang)]
        for ig in rows:
            lines.append(f"· [{ig.account}] {ig.sender_norm}")
        return "\n".join(lines)
    finally:
        conn.close()


def add_ignored(data_dir: Path, account: str, sender: str) -> str:
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el

    lang = load_locale(data_dir).lang
    conn = open_db(data_dir)
    try:
        el.add_ignored_sender(conn, account.strip(), sender.strip())
        return t(
            "email_label.ignore_added",
            lang,
            account=account.strip(),
            sender=sender.strip(),
        )
    finally:
        conn.close()


def remove_ignored(data_dir: Path, account: str, sender: str) -> str:
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el

    lang = load_locale(data_dir).lang
    conn = open_db(data_dir)
    try:
        removed = el.remove_ignored_sender(conn, account.strip(), sender.strip())
        if not removed:
            return t("email_label.ignore_not_found", lang)
        return t(
            "email_label.ignore_removed",
            lang,
            account=account.strip(),
            sender=sender.strip(),
        )
    finally:
        conn.close()
