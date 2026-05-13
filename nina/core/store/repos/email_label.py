"""PostgreSQL persistence for learned Gmail labels (per account)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg


@dataclass
class SenderRule:
    account: str
    sender_norm: str
    label_name: str
    archive_inbox: bool = True


@dataclass(frozen=True)
class ListedSenderRule:
    """Row from ``email_sender_rules`` including ``created_at``."""

    account: str
    sender_norm: str
    label_name: str
    archive_inbox: bool
    created_at: datetime


@dataclass(frozen=True)
class IgnoredSender:
    account: str
    sender_norm: str
    created_at: datetime


@dataclass
class PendingLabel:
    id: str
    account: str
    sender_norm: str
    sender_raw: str
    sample_subject: str
    hit_count: int
    notified: bool
    status: str


def _row_rule(row: dict) -> SenderRule:
    return SenderRule(
        account=row["account"],
        sender_norm=row["sender_norm"],
        label_name=row["label_name"],
        archive_inbox=bool(row["archive_inbox"]),
    )


def _row_pending(row: dict) -> PendingLabel:
    return PendingLabel(
        id=row["id"],
        account=row["account"],
        sender_norm=row["sender_norm"],
        sender_raw=row["sender_raw"],
        sample_subject=row.get("sample_subject") or "",
        hit_count=int(row["hit_count"]),
        notified=bool(row["notified"]),
        status=row["status"],
    )


def upsert_seen_message(
    conn: psycopg.Connection[dict],
    account: str,
    message_id: str,
    thread_id: str,
    sender_raw: str,
    sender_norm: str,
    subject: str,
    msg_date: str,
) -> None:
    conn.execute(
        """
        INSERT INTO email_messages (
            account, message_id, thread_id, sender_raw, sender_norm,
            subject, msg_date, first_seen_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (account, message_id) DO UPDATE SET
            sender_raw   = EXCLUDED.sender_raw,
            sender_norm  = EXCLUDED.sender_norm,
            subject      = EXCLUDED.subject,
            msg_date     = EXCLUDED.msg_date
        """,
        (account, message_id, thread_id, sender_raw, sender_norm, subject, msg_date),
    )
    conn.commit()


def get_rule(
    conn: psycopg.Connection[dict], account: str, sender_norm: str
) -> SenderRule | None:
    row = conn.execute(
        """
        SELECT account, sender_norm, label_name, archive_inbox
        FROM email_sender_rules
        WHERE account = %s AND sender_norm = %s
        """,
        (account, sender_norm),
    ).fetchone()
    return _row_rule(row) if row else None


def list_rules(
    conn: psycopg.Connection[dict],
    *,
    account: str | None = None,
) -> list[ListedSenderRule]:
    """All learned sender→label rules, optionally filtered by Gmail account."""
    if account is not None:
        rows = conn.execute(
            """
            SELECT account, sender_norm, label_name, archive_inbox, created_at
            FROM email_sender_rules
            WHERE account = %s
            ORDER BY sender_norm
            """,
            (account,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT account, sender_norm, label_name, archive_inbox, created_at
            FROM email_sender_rules
            ORDER BY account, sender_norm
            """
        ).fetchall()
    return [
        ListedSenderRule(
            account=str(r["account"]),
            sender_norm=str(r["sender_norm"]),
            label_name=str(r["label_name"]),
            archive_inbox=bool(r["archive_inbox"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


def upsert_rule(conn: psycopg.Connection[dict], rule: SenderRule) -> None:
    conn.execute(
        """
        INSERT INTO email_sender_rules (
            account, sender_norm, label_name, archive_inbox, created_at
        )
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (account, sender_norm) DO UPDATE SET
            label_name     = EXCLUDED.label_name,
            archive_inbox  = EXCLUDED.archive_inbox
        """,
        (rule.account, rule.sender_norm, rule.label_name, rule.archive_inbox),
    )
    conn.commit()


def count_sender_in_window(
    conn: psycopg.Connection[dict],
    account: str,
    sender_norm: str,
    days: int = 30,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM email_messages
        WHERE account = %s
          AND sender_norm = %s
          AND first_seen_at >= (now() - (%s * INTERVAL '1 day'))
        """,
        (account, sender_norm, days),
    ).fetchone()
    return int(row["c"]) if row else 0


def find_open_pending(
    conn: psycopg.Connection[dict], account: str, sender_norm: str
) -> PendingLabel | None:
    row = conn.execute(
        """
        SELECT id, account, sender_norm, sender_raw, sample_subject,
               hit_count, notified, status
        FROM email_pending_labels
        WHERE account = %s AND sender_norm = %s AND status = 'open'
        """,
        (account, sender_norm),
    ).fetchone()
    return _row_pending(row) if row else None


def list_open_pending(conn: psycopg.Connection[dict]) -> list[PendingLabel]:
    rows = conn.execute(
        """
        SELECT id, account, sender_norm, sender_raw, sample_subject,
               hit_count, notified, status
        FROM email_pending_labels
        WHERE status = 'open'
        ORDER BY created_at DESC
        """
    ).fetchall()
    return [_row_pending(r) for r in rows]


def get_pending_by_id_prefix(
    conn: psycopg.Connection[dict], id_prefix: str
) -> PendingLabel | None:
    rows = conn.execute(
        """
        SELECT id, account, sender_norm, sender_raw, sample_subject,
               hit_count, notified, status
        FROM email_pending_labels
        WHERE status = 'open' AND id LIKE %s
        """,
        (f"{id_prefix}%",),
    ).fetchall()
    if not rows:
        return None
    if len(rows) > 1:
        raise ValueError("ambiguous pending id prefix")
    return _row_pending(rows[0])


def insert_pending(
    conn: psycopg.Connection[dict],
    pending_id: str,
    account: str,
    sender_norm: str,
    sender_raw: str,
    sample_subject: str,
    hit_count: int,
) -> None:
    conn.execute(
        """
        INSERT INTO email_pending_labels (
            id, account, sender_norm, sender_raw, sample_subject,
            hit_count, notified, status, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, false, 'open', now())
        """,
        (pending_id, account, sender_norm, sender_raw, sample_subject, hit_count),
    )
    conn.commit()


def update_pending_hit(
    conn: psycopg.Connection[dict],
    pending_id: str,
    hit_count: int,
    sample_subject: str,
) -> None:
    conn.execute(
        """
        UPDATE email_pending_labels
        SET hit_count = GREATEST(hit_count, %s),
            sample_subject = CASE
                WHEN %s <> '' THEN %s ELSE sample_subject END
        WHERE id = %s AND status = 'open'
        """,
        (hit_count, sample_subject, sample_subject, pending_id),
    )
    conn.commit()


def set_pending_notified(conn: psycopg.Connection[dict], pending_id: str) -> None:
    conn.execute(
        "UPDATE email_pending_labels SET notified = true WHERE id = %s",
        (pending_id,),
    )
    conn.commit()


def dismiss_pending(conn: psycopg.Connection[dict], pending_id: str) -> bool:
    cur = conn.execute(
        """
        UPDATE email_pending_labels
        SET status = 'dismissed'
        WHERE id = %s AND status = 'open'
        """,
        (pending_id,),
    )
    conn.commit()
    return cur.rowcount > 0


def dismiss_pending_for_sender(
    conn: psycopg.Connection[dict], account: str, sender_norm: str
) -> int:
    cur = conn.execute(
        """
        UPDATE email_pending_labels
        SET status = 'dismissed'
        WHERE account = %s AND sender_norm = %s AND status = 'open'
        """,
        (account, sender_norm),
    )
    conn.commit()
    return cur.rowcount


def dismiss_all_pending(conn: psycopg.Connection[dict]) -> int:
    cur = conn.execute(
        "UPDATE email_pending_labels SET status = 'dismissed' WHERE status = 'open'"
    )
    conn.commit()
    return cur.rowcount


def close_pending_taught(conn: psycopg.Connection[dict], pending_id: str) -> None:
    conn.execute(
        "UPDATE email_pending_labels SET status = 'taught' WHERE id = %s",
        (pending_id,),
    )
    conn.commit()


def list_untagged_for_sender(
    conn: psycopg.Connection[dict],
    account: str,
    sender_norm: str,
    limit: int = 80,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT message_id
        FROM email_messages
        WHERE account = %s AND sender_norm = %s AND tagged_at IS NULL
        ORDER BY first_seen_at DESC
        LIMIT %s
        """,
        (account, sender_norm, limit),
    ).fetchall()
    return [r["message_id"] for r in rows]


def mark_messages_tagged(
    conn: psycopg.Connection[dict],
    account: str,
    message_ids: list[str],
    label_name: str,
) -> None:
    if not message_ids:
        return
    for mid in message_ids:
        conn.execute(
            """
            UPDATE email_messages
            SET tagged_at = now(), label_applied = %s
            WHERE account = %s AND message_id = %s
            """,
            (label_name, account, mid),
        )
    conn.commit()


def is_message_tagged(
    conn: psycopg.Connection[dict], account: str, message_id: str
) -> bool:
    row = conn.execute(
        """
        SELECT tagged_at FROM email_messages
        WHERE account = %s AND message_id = %s
        """,
        (account, message_id),
    ).fetchone()
    return bool(row and row.get("tagged_at"))


def is_sender_ignored(
    conn: psycopg.Connection[dict], account: str, sender_norm: str
) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM email_ignored_senders
        WHERE account = %s AND sender_norm = %s
        """,
        (account, sender_norm),
    ).fetchone()
    return row is not None


def add_ignored_sender(
    conn: psycopg.Connection[dict], account: str, sender_norm: str
) -> None:
    conn.execute(
        """
        INSERT INTO email_ignored_senders (account, sender_norm, created_at)
        VALUES (%s, %s, now())
        ON CONFLICT (account, sender_norm) DO NOTHING
        """,
        (account, sender_norm),
    )
    conn.commit()


def remove_ignored_sender(
    conn: psycopg.Connection[dict], account: str, sender_norm: str
) -> bool:
    cur = conn.execute(
        """
        DELETE FROM email_ignored_senders
        WHERE account = %s AND sender_norm = %s
        """,
        (account, sender_norm),
    )
    conn.commit()
    return cur.rowcount > 0


def list_ignored_senders(
    conn: psycopg.Connection[dict],
    *,
    account: str | None = None,
) -> list[IgnoredSender]:
    if account is not None:
        rows = conn.execute(
            """
            SELECT account, sender_norm, created_at
            FROM email_ignored_senders
            WHERE account = %s
            ORDER BY sender_norm
            """,
            (account,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT account, sender_norm, created_at
            FROM email_ignored_senders
            ORDER BY account, sender_norm
            """
        ).fetchall()
    return [
        IgnoredSender(
            account=str(r["account"]),
            sender_norm=str(r["sender_norm"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


def find_candidate_senders(
    conn: psycopg.Connection[dict],
    *,
    min_hits: int = 3,
    window_days: int = 120,
    account: str | None = None,
) -> list[dict]:
    """Senders in email_messages without a rule and not ignored, with enough hits."""
    params: list = [window_days, min_hits]
    acct_filter = ""
    if account is not None:
        acct_filter = "AND m.account = %s"
        params.append(account)
    rows = conn.execute(
        f"""
        SELECT m.account, m.sender_norm,
               MAX(m.sender_raw) AS sender_raw,
               MAX(m.subject) AS sample_subject,
               COUNT(*) AS hit_count
        FROM email_messages m
        WHERE m.tagged_at IS NULL
          AND m.first_seen_at >= now() - (%s * INTERVAL '1 day')
          {acct_filter}
        GROUP BY m.account, m.sender_norm
        HAVING COUNT(*) >= %s
        ORDER BY hit_count DESC
        """,
        params,
    ).fetchall()

    results: list[dict] = []
    for row in rows:
        acct = row["account"]
        norm = row["sender_norm"]
        if get_rule(conn, acct, norm) is not None:
            continue
        if is_sender_ignored(conn, acct, norm):
            continue
        existing = find_open_pending(conn, acct, norm)
        if existing:
            update_pending_hit(
                conn, existing.id, int(row["hit_count"]),
                (row.get("sample_subject") or "")[:500],
            )
            continue
        results.append({
            "account": acct,
            "sender_norm": norm,
            "sender_raw": row["sender_raw"] or norm,
            "sample_subject": (row.get("sample_subject") or "")[:500],
            "hit_count": int(row["hit_count"]),
        })
    return results
