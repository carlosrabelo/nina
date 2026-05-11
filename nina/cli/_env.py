"""Shared CLI helpers for resolving runtime paths from environment."""

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv


def _running_inside_docker() -> bool:
    return Path("/.dockerenv").exists()


def _apply_host_env_overrides() -> None:
    """Prefer `*_HOST` values when Nina runs on the host (not in a container).

    Typical `.env` keeps Compose-friendly `DATABASE_URL` (hostname `postgres`)
    and parallel `DATABASE_URL_HOST` / path `*_HOST` for local `nina` / `make run`.
    The Makefile used to export these; Python applies the same mapping here.
    """
    if _running_inside_docker():
        return
    pairs = (
        ("DATABASE_URL_HOST", "DATABASE_URL"),
        ("DATA_DIR_HOST", "DATA_DIR"),
        ("TOKENS_DIR_HOST", "TOKENS_DIR"),
        ("SESSIONS_DIR_HOST", "SESSIONS_DIR"),
        ("GOOGLE_CREDENTIALS_FILE_HOST", "GOOGLE_CREDENTIALS_FILE"),
    )
    for host_key, target_key in pairs:
        val = os.environ.get(host_key, "").strip()
        if val:
            os.environ[target_key] = val


def load_project_dotenv() -> None:
    """Load the nearest `.env` walking up from the current working directory.

    Does not override variables already set in the process environment.
    After loading, applies ``*_HOST`` overrides when not inside Docker (see
    :func:`_apply_host_env_overrides`).
    """
    path = find_dotenv(filename=".env", usecwd=True)
    load_dotenv(dotenv_path=path or None, override=False)
    _apply_host_env_overrides()


def tokens_dir() -> Path:
    load_project_dotenv()
    return Path(os.environ.get("TOKENS_DIR", "tokens"))


def credentials_file() -> Path:
    load_project_dotenv()
    return Path(
        os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials/credentials.json")
    )
