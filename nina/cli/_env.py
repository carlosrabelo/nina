"""Shared CLI helpers for resolving runtime paths from environment."""

import os
from pathlib import Path
from urllib.parse import quote, quote_plus

from dotenv import find_dotenv, load_dotenv


def _running_inside_docker() -> bool:
    return Path("/.dockerenv").exists()


_DATA_MOUNT_PATH_KEYS = (
    "DATA_DIR",
    "TOKENS_DIR",
    "SESSIONS_DIR",
    "GOOGLE_CREDENTIALS_FILE",
)


def _absolutize_relative_data_paths_in_docker() -> None:
    """Turn repo-style paths into absolute paths under the container volume.

    On the host, ``data/db`` resolves from the process cwd. In Docker the same
    ``.env`` values must point at the mounted tree (``./data:/data``), so a
    leading ``/`` is added when the value is non-empty and not already absolute.
    """
    if not _running_inside_docker():
        return
    for key in _DATA_MOUNT_PATH_KEYS:
        val = os.environ.get(key, "").strip()
        if not val or val.startswith("/"):
            continue
        os.environ[key] = "/" + val


def _build_database_url_from_postgres_env() -> str | None:
    """Build ``postgresql://...`` from ``POSTGRES_*`` if all required parts exist."""
    user = os.environ.get("POSTGRES_USER", "").strip()
    password = os.environ.get("POSTGRES_PASSWORD", "").strip()
    db = os.environ.get("POSTGRES_DB", "").strip()
    if not user or not password or not db:
        return None

    port_s = os.environ.get("POSTGRES_PORT", "").strip() or "5432"
    try:
        port = int(port_s)
    except ValueError:
        return None

    host_override = os.environ.get("POSTGRES_HOST", "").strip()
    if host_override:
        host = host_override
    elif _running_inside_docker():
        host = "postgres"
    else:
        host = "127.0.0.1"

    pw_enc = quote_plus(password)
    user_enc = quote_plus(user)
    db_enc = quote(db, safe="")
    return f"postgresql://{user_enc}:{pw_enc}@{host}:{port}/{db_enc}"


def _ensure_database_url() -> None:
    """Set ``DATABASE_URL`` from ``POSTGRES_*`` when it is still unset or blank."""
    if os.environ.get("DATABASE_URL", "").strip():
        return
    built = _build_database_url_from_postgres_env()
    if built:
        os.environ["DATABASE_URL"] = built


def load_project_dotenv() -> None:
    """Load the nearest `.env` walking up from the current working directory.

    Does not override variables already set in the process environment.
    After loading:

    1. Inside Docker, prepends ``/`` to relative ``DATA_DIR`` / ``TOKENS_DIR`` /
       ``SESSIONS_DIR`` / ``GOOGLE_CREDENTIALS_FILE`` so ``data/...`` maps to
       ``/data/...`` (see :func:`_absolutize_relative_data_paths_in_docker`).
    2. If ``DATABASE_URL`` is still empty, builds it from ``POSTGRES_USER``,
       ``POSTGRES_PASSWORD``, ``POSTGRES_DB``, optional ``POSTGRES_PORT`` /
       ``POSTGRES_HOST`` (recommended single-source setup for local + Docker).
    """
    path = find_dotenv(filename=".env", usecwd=True)
    load_dotenv(dotenv_path=path or None, override=False)
    _absolutize_relative_data_paths_in_docker()
    _ensure_database_url()


def tokens_dir() -> Path:
    load_project_dotenv()
    return Path(os.environ.get("TOKENS_DIR", "tokens"))


def credentials_file() -> Path:
    load_project_dotenv()
    return Path(
        os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials/credentials.json")
    )
