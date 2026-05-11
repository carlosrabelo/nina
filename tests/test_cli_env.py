"""Tests for CLI .env loading and Docker path normalization."""

import os
from unittest.mock import patch

import pytest

from nina.cli import _env


def test_build_db_url_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "nina")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_DB", "nina")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with patch.object(_env, "_running_inside_docker", return_value=False):
        url = _env._build_database_url_from_postgres_env()
    assert url == "postgresql://nina:secret@127.0.0.1:5432/nina"


def test_build_db_url_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "nina")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_DB", "nina")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    with patch.object(_env, "_running_inside_docker", return_value=True):
        url = _env._build_database_url_from_postgres_env()
    assert url == "postgresql://nina:secret@postgres:5432/nina"


def test_build_db_url_custom_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "nina")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_DB", "nina")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    with patch.object(_env, "_running_inside_docker", return_value=True):
        url = _env._build_database_url_from_postgres_env()
    assert url == "postgresql://nina:secret@db.internal:5432/nina"


def test_build_db_url_password_quoted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@:s")
    monkeypatch.setenv("POSTGRES_DB", "d")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    with patch.object(_env, "_running_inside_docker", return_value=False):
        url = _env._build_database_url_from_postgres_env()
    assert url == "postgresql://u:p%40%3As@127.0.0.1:5432/d"


def test_build_db_url_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.setenv("POSTGRES_DB", "d")
    assert _env._build_database_url_from_postgres_env() is None


def test_ensure_db_url_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://a:b@c:1/d")
    monkeypatch.setenv("POSTGRES_USER", "x")
    monkeypatch.setenv("POSTGRES_PASSWORD", "y")
    monkeypatch.setenv("POSTGRES_DB", "z")
    _env._ensure_database_url()
    assert os.environ["DATABASE_URL"] == "postgresql://a:b@c:1/d"


def test_ensure_db_url_from_pg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "nina")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_DB", "nina")
    monkeypatch.setenv("POSTGRES_PORT", "9999")
    with patch.object(_env, "_running_inside_docker", return_value=False):
        _env._ensure_database_url()
    assert os.environ["DATABASE_URL"] == "postgresql://nina:secret@127.0.0.1:9999/nina"


def test_absolutize_paths_in_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", "data/db")
    monkeypatch.setenv("TOKENS_DIR", "data/tokens")
    monkeypatch.setenv("SESSIONS_DIR", "data/sessions")
    monkeypatch.setenv("GOOGLE_CREDENTIALS_FILE", "data/credentials/credentials.json")
    with patch.object(_env, "_running_inside_docker", return_value=True):
        _env._absolutize_relative_data_paths_in_docker()
    assert os.environ["DATA_DIR"] == "/data/db"
    assert os.environ["TOKENS_DIR"] == "/data/tokens"
    assert os.environ["SESSIONS_DIR"] == "/data/sessions"
    assert os.environ["GOOGLE_CREDENTIALS_FILE"] == "/data/credentials/credentials.json"


def test_absolutize_skips_absolute_in_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", "/data/db")
    with patch.object(_env, "_running_inside_docker", return_value=True):
        _env._absolutize_relative_data_paths_in_docker()
    assert os.environ["DATA_DIR"] == "/data/db"


def test_absolutize_skipped_off_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", "data/db")
    with patch.object(_env, "_running_inside_docker", return_value=False):
        _env._absolutize_relative_data_paths_in_docker()
    assert os.environ["DATA_DIR"] == "data/db"


def test_absolutize_empty_string_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", "")
    with patch.object(_env, "_running_inside_docker", return_value=True):
        _env._absolutize_relative_data_paths_in_docker()
    assert os.environ.get("DATA_DIR") == ""
