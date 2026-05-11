"""Periodic Gmail ingest + learned labels (per account)."""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def make_job(tokens_dir: Path, data_dir: Path, bot_token: str, owner_id: int):  # type: ignore[no-untyped-def]
    """Return APScheduler job: sync inbox, apply rules, Telegram suggestions."""

    def job() -> None:
        try:
            from nina.skills.email_learning.service import run_email_learning_sync

            run_email_learning_sync(
                tokens_dir,
                data_dir,
                bot_token=bot_token,
                owner_id=owner_id,
                send_telegram=True,
            )
        except Exception as e:
            log.warning("email learning job failed: %s", e)

    return job
