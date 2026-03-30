# nina/scheduler/runner.py
"""Scheduler — keeps Nina running and triggers jobs on a defined schedule.

Design: wraps APScheduler's BackgroundScheduler so jobs are registered
in one place and the main thread just blocks until a shutdown signal.

Usage::

    make scheduler          # run from CLI
    ./nina.py scheduler     # or directly

Adding a job (in a jobs/ module)::

    from nina.core.scheduler.runner import scheduler

    @scheduler.scheduled_job("cron", hour=7, minute=0)
    def daily_brief():
        ...

    @scheduler.scheduled_job("interval", minutes=1)
    def check_telegram():
        ...
"""

import logging
import signal
import time

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)


class Scheduler:
    """Nina's internal scheduler.

    Wraps APScheduler and provides a clean start/stop interface.
    Jobs are registered via :attr:`apscheduler` or the convenience
    :meth:`add_job` method.
    """

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(timezone="UTC")
        self._running = False

    # ------------------------------------------------------------------
    # Job registration
    # ------------------------------------------------------------------

    def add_job(self, func, trigger: str, **trigger_kwargs) -> None:  # type: ignore[no-untyped-def]
        """Register a job.

        Args:
            func: Callable to execute.
            trigger: ``"cron"``, ``"interval"``, or ``"date"``.
            **trigger_kwargs: Passed directly to APScheduler.

        Example::

            scheduler.add_job(my_func, "cron", hour=7, minute=0)
            scheduler.add_job(my_func, "interval", minutes=5)
        """
        self._scheduler.add_job(func, trigger, **trigger_kwargs)
        log.info("job registered: %s  trigger=%s %s", func.__name__, trigger, trigger_kwargs)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler (non-blocking — jobs run in background threads)."""
        self._scheduler.start()
        self._running = True
        log.info("scheduler started — %d job(s) registered", len(self._scheduler.get_jobs()))

    def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        if self._running:
            self._scheduler.shutdown(wait=True)
            self._running = False
            log.info("scheduler stopped")

    def run_forever(self) -> None:
        """Start and block until SIGINT or SIGTERM.

        This is the main entry point when running Nina as a daemon.
        """
        self.start()

        def _shutdown(sig, frame) -> None:  # type: ignore[no-untyped-def]
            log.info("signal %s received — shutting down", sig)
            self.stop()

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        log.info("Nina scheduler running — press Ctrl+C to stop")
        while self._running:
            time.sleep(1)

    @property
    def job_count(self) -> int:
        return len(self._scheduler.get_jobs())
