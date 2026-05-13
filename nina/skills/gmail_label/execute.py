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
        return t("gmail_label.id_too_short", lang)
    label_name = label_name.strip()
    if not label_name:
        return t("gmail_label.label_empty", lang)
    if not label_name.startswith(("@", "!")):
        return t("gmail_label.label_must_at", lang)

    conn = open_db(data_dir)
    try:
        try:
            pending = el.get_pending_by_id_prefix(conn, id_prefix)
        except ValueError:
            return t("gmail_label.ambiguous_id", lang)

        if pending is None:
            return t("gmail_label.pending_not_found", lang)

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
            "gmail_label.taught_ok",
            lang,
            sender=pending.sender_norm,
            label=label_name,
            account=pending.account,
            applied=len(applied_ids),
        )
    finally:
        conn.close()


def add_rule_direct(
    data_dir: Path,
    account: str,
    sender: str,
    label_name: str,
) -> str:
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el
    from nina.core.store.repos.email_label import SenderRule

    lang = load_locale(data_dir).lang
    account = account.strip()
    sender = sender.strip().lower()
    label_name = label_name.strip()
    if not label_name.startswith(("@", "!")):
        return t("gmail_label.label_must_at", lang)

    conn = open_db(data_dir)
    try:
        existing = el.get_rule(conn, account, sender)
        el.upsert_rule(
            conn,
            SenderRule(
                account=account,
                sender_norm=sender,
                label_name=label_name,
                archive_inbox=True,
            ),
        )
        key = "gmail_label.rule_updated" if existing else "gmail_label.rule_added"
        return t(key, lang, sender=sender, label=label_name, account=account,
                 old_label=existing.label_name if existing else "")
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
        return t("gmail_label.dismiss_all_ok", lang, count=count)
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
        return t("gmail_label.id_too_short", lang)
    conn = open_db(data_dir)
    try:
        try:
            pending = el.get_pending_by_id_prefix(conn, id_prefix)
        except ValueError:
            return t("gmail_label.ambiguous_id", lang)
        if pending is None:
            return t("gmail_label.pending_not_found", lang)
        if not el.dismiss_pending(conn, pending.id):
            return t("gmail_label.pending_not_found", lang)
        el.add_ignored_sender(conn, pending.account, pending.sender_norm)
        return t("gmail_label.dismiss_ok", lang, sender=pending.sender_norm)
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
            return t("gmail_label.no_pending", lang)
        lines = [t("gmail_label.pending_header", lang)]
        for p in rows:
            lines.append(
                t(
                    "gmail_label.pending_line",
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
            return t("gmail_label.ignore_empty", lang)
        lines = [t("gmail_label.ignore_header", lang)]
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
    acct = account.strip()
    snd = sender.strip()
    conn = open_db(data_dir)
    try:
        el.add_ignored_sender(conn, acct, snd)
        cleaned = el.dismiss_pending_for_sender(conn, acct, snd)
        return t(
            "gmail_label.ignore_added",
            lang,
            account=acct,
            sender=snd,
            cleaned=cleaned,
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
            return t("gmail_label.ignore_not_found", lang)
        return t(
            "gmail_label.ignore_removed",
            lang,
            account=account.strip(),
            sender=sender.strip(),
        )
    finally:
        conn.close()


def check_rules(data_dir: Path, tokens_dir: Path) -> str:
    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el
    from nina.errors import ConfigError
    from nina.integrations.google.auth import discover_accounts
    from nina.integrations.google.gmail.client import GmailMultiClient

    lang = load_locale(data_dir).lang
    conn = open_db(data_dir)
    issues: list[str] = []

    try:
        rules = el.list_rules(conn)
        if not rules:
            return t("gmail_label.check_no_rules", lang)

        valid_accounts = discover_accounts(tokens_dir)
        gmail_labels_by_account: dict[str, set[str]] = {}

        try:
            multi = GmailMultiClient.from_env()
            for acct in multi.accounts:
                try:
                    label_map = multi.client(acct).list_user_label_map()
                    gmail_labels_by_account[acct] = set(label_map.values())
                except Exception:
                    gmail_labels_by_account[acct] = None
        except ConfigError:
            pass

        ignored_pairs: set[tuple[str, str]] = set()
        ignored = el.list_ignored_senders(conn)
        for ig in ignored:
            ignored_pairs.add((ig.account, ig.sender_norm))

        for rule in rules:
            if not rule.label_name.startswith(("@", "!")):
                issues.append(
                    t("gmail_label.check_bad_prefix", lang,
                      account=rule.account, sender=rule.sender_norm,
                      label=rule.label_name)
                )

            if (rule.account, rule.sender_norm) in ignored_pairs:
                issues.append(
                    t("gmail_label.check_ignored", lang,
                      account=rule.account, sender=rule.sender_norm,
                      label=rule.label_name)
                )

            if rule.account not in valid_accounts:
                issues.append(
                    t("gmail_label.check_no_token", lang,
                      account=rule.account, sender=rule.sender_norm,
                      label=rule.label_name)
                )

            labels_set = gmail_labels_by_account.get(rule.account)
            if labels_set is not None and rule.label_name not in labels_set:
                issues.append(
                    t("gmail_label.check_missing_label", lang,
                      account=rule.account, sender=rule.sender_norm,
                      label=rule.label_name)
                )

        if not issues:
            return t("gmail_label.check_ok", lang, count=len(rules))

        header = t("gmail_label.check_header", lang,
                   count=len(issues), rules=len(rules))
        return header + "\n" + "\n".join(f"  {i}" for i in issues)
    finally:
        conn.close()


def scan_pending_suggestions(
    data_dir: Path,
    *,
    min_hits: int | None = None,
    window_days: int | None = None,
    account: str | None = None,
    verbose: bool = False,
) -> str:
    import os
    import sys
    import uuid

    from nina.core.i18n import t
    from nina.core.locale.store import load as load_locale
    from nina.core.store.db import open_db
    from nina.core.store.repos import email_label as el

    lang = load_locale(data_dir).lang
    if min_hits is None:
        min_hits = max(1, int(os.environ.get("NINA_EMAIL_LABEL_MIN_HITS", "3")))
    if window_days is None:
        window_days = max(1, int(os.environ.get("NINA_EMAIL_LABEL_WINDOW_DAYS", "120")))

    conn = open_db(data_dir)
    try:
        candidates = el.find_candidate_senders(
            conn,
            min_hits=min_hits,
            window_days=window_days,
            account=account,
        )
        if not candidates:
            return t("gmail_label.scan_none", lang)

        created = 0
        for c in candidates:
            pid = uuid.uuid4().hex
            el.insert_pending(
                conn,
                pid,
                c["account"],
                c["sender_norm"],
                c["sender_raw"],
                c["sample_subject"],
                c["hit_count"],
            )
            created += 1
            if verbose:
                print(
                    f"  [{c['account']}] {c['sender_norm']} "
                    f"({c['hit_count']} msgs) -> {pid[:12]}",
                    file=sys.stderr,
                    flush=True,
                )

        return t("gmail_label.scan_done", lang, count=created)
    finally:
        conn.close()
