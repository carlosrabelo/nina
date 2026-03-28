# nina/scheduler/jobs/obsidian_sync.py
"""Obsidian sync job — writes daily note, open.md and week.md to the vault."""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def make_job(tokens_dir: Path, data_dir: Path) -> object:
    """Return the job function bound to the given context."""

    def job() -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from nina.google.auth import discover_accounts
        from nina.locale.store import load as load_locale
        from nina.obsidian import vault_path, ensure_folders, write_page
        from nina.obsidian.open_page import render as render_open
        from nina.obsidian.today_page import render as render_today
        from nina.obsidian.week_page import render as render_week
        from nina.store.db import open_db
        from nina.workdays.store import load as load_workdays

        if vault_path() is None:
            return  # vault not configured — skip silently

        lang = load_locale(data_dir).lang
        schedule = load_workdays(data_dir)
        accounts = discover_accounts(tokens_dir)
        conn = open_db(data_dir)
        tz = ZoneInfo(schedule.timezone)
        today_date = datetime.now(tz).strftime("%Y-%m-%d")

        ensure_folders()

        # ── daily note ────────────────────────────────────────────────────────
        try:
            content = render_today(
                conn=conn,
                accounts=accounts,
                tokens_dir=tokens_dir,
                timezone_name=schedule.timezone,
                lang=lang,
            )
            write_page(f"{today_date}.md", content, subfolder="daily")
            write_page("today.md", f"![[daily/{today_date}]]\n")
        except Exception as e:
            log.warning("obsidian daily note failed: %s", e)

        # ── open.md ───────────────────────────────────────────────────────────
        try:
            write_page("open.md", render_open(conn=conn, lang=lang))
        except Exception as e:
            log.warning("obsidian open.md failed: %s", e)

        # ── week.md ───────────────────────────────────────────────────────────
        try:
            content = render_week(
                conn=conn,
                accounts=accounts,
                tokens_dir=tokens_dir,
                timezone_name=schedule.timezone,
                lang=lang,
            )
            write_page("week.md", content)
        except Exception as e:
            log.warning("obsidian week.md failed: %s", e)

    return job
