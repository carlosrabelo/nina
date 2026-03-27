# tests/test_scheduler.py
"""Tests for the scheduler runner."""

from unittest.mock import MagicMock, patch

import pytest

from nina.scheduler.runner import Scheduler


@pytest.fixture()
def scheduler() -> Scheduler:
    return Scheduler()


def test_initial_job_count_is_zero(scheduler: Scheduler) -> None:
    assert scheduler.job_count == 0


def test_add_job_registers_job(scheduler: Scheduler) -> None:
    def dummy() -> None:
        pass

    with patch.object(scheduler._scheduler, "add_job") as mock_add:
        scheduler.add_job(dummy, "interval", minutes=5)
        mock_add.assert_called_once_with(dummy, "interval", minutes=5)


def test_start_starts_apscheduler(scheduler: Scheduler) -> None:
    with patch.object(scheduler._scheduler, "start") as mock_start, \
         patch.object(scheduler._scheduler, "get_jobs", return_value=[]):
        scheduler.start()
        mock_start.assert_called_once()
        assert scheduler._running is True


def test_stop_shuts_down_apscheduler(scheduler: Scheduler) -> None:
    scheduler._running = True
    with patch.object(scheduler._scheduler, "shutdown") as mock_shutdown:
        scheduler.stop()
        mock_shutdown.assert_called_once_with(wait=True)
        assert scheduler._running is False


def test_stop_is_idempotent_when_not_running(scheduler: Scheduler) -> None:
    with patch.object(scheduler._scheduler, "shutdown") as mock_shutdown:
        scheduler.stop()
        mock_shutdown.assert_not_called()
