"""Tests for CLI .env loading and host overrides."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from nina.cli import _env


def test_apply_host_overrides_when_not_in_docker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL_HOST", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://nina:nina@postgres:5432/nina")
    monkeypatch.setenv("DATABASE_URL_HOST", "postgresql://nina:nina@localhost:5432/nina")
    monkeypatch.setenv("DATA_DIR", "/data/db")
    monkeypatch.setenv("DATA_DIR_HOST", "data/db")

    with patch.object(_env, "_running_inside_docker", return_value=False):
        _env._apply_host_env_overrides()

    assert os.environ["DATABASE_URL"] == "postgresql://nina:nina@localhost:5432/nina"
    assert os.environ["DATA_DIR"] == "data/db"


def test_apply_host_overrides_skipped_in_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://nina:nina@postgres:5432/nina")
    monkeypatch.setenv("DATABASE_URL_HOST", "postgresql://nina:nina@localhost:5432/nina")

    with patch.object(_env, "_running_inside_docker", return_value=True):
        _env._apply_host_env_overrides()

    assert os.environ["DATABASE_URL"] == "postgresql://nina:nina@postgres:5432/nina"


def test_apply_host_overrides_empty_host_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://nina:nina@postgres:5432/nina")
    monkeypatch.delenv("DATABASE_URL_HOST", raising=False)

    with patch.object(_env, "_running_inside_docker", return_value=False):
        _env._apply_host_env_overrides()

    assert os.environ["DATABASE_URL"] == "postgresql://nina:nina@postgres:5432/nina"
