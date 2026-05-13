"""Periodic Gmail process: ingest headers, apply rules, discover pending suggestions."""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def make_job(tokens_dir: Path, data_dir: Path):  # type: ignore[no-untyped-def]
    """Return APScheduler job: process inbox, apply rules, and create pending suggestions."""

    def job() -> None:
        try:
            from nina.tasks.email_process import run_email_label_process

            run_email_label_process(
                tokens_dir,
                data_dir,
                discover_pending=True,
            )
        except Exception as e:
            log.warning("email learning job failed: %s", e)

    return job
