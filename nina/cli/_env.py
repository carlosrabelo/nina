"""Shared CLI helpers for resolving runtime paths from environment."""

import os
from pathlib import Path

from dotenv import load_dotenv


def tokens_dir() -> Path:
    load_dotenv()
    return Path(os.environ.get("TOKENS_DIR", "tokens"))


def credentials_file() -> Path:
    load_dotenv()
    return Path(
        os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials/credentials.json")
    )
