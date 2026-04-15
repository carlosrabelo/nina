"""End-of-day reminder scheduler job.

Runs at configured time (default 18:00) and prompts the user via Telegram
to log their day's activities if they haven't already.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)


def make_eod_job(
    tokens_dir: Path,
    data_dir: Path,
    bot_token: str,
    owner_id: int,
):
    """Return the EOD reminder job function bound to the given context."""

    def _send_telegram(text: str) -> None:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps({
            "chat_id": owner_id,
            "text": text,
            "parse_mode": "HTML",
        }).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            log.warning("EOD: telegram send failed: %s", e)

    def job() -> None:
        try:
            from nina.core.locale.store import load as load_locale
            from nina.skills.activity_log.eod_prompt import get_eod_prompt
            from nina.skills.activity_log.google_reader import query_activities
            from nina.skills.presence.store import load as load_presence
            from nina.skills.profile.store import load as load_profile
            from nina.skills.workdays.checker import get_context
            from nina.skills.workdays.store import load as load_workdays

            presence = load_presence(data_dir)
            schedule = load_workdays(data_dir)
            lang = load_locale(data_dir).lang
            ctx = get_context(schedule, presence, lang)

            if ctx.is_work_time:
                # Still working — don't prompt yet
                return

            # Already left work — check if activities were logged
            profile = load_profile(data_dir)
            cal_accounts = profile.for_presence(presence.status).calendar
            if not cal_accounts:
                log.info("EOD: skipped — no calendar account")
                return

            entries = query_activities(
                account=cal_accounts[0],
                tokens_dir=tokens_dir,
                target_date=datetime.now().date(),
            )
            if not entries:
                _send_telegram(get_eod_prompt(lang))
                log.info("EOD: prompted user (no activities logged)")
            else:
                log.info(
                    "EOD: skipped — %d activities logged", len(entries),
                )
        except Exception as e:
            log.warning("EOD: job error: %s", e)

    return job
