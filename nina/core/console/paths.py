"""Paths and locale for the interactive console (env + data dir)."""

import os
from pathlib import Path

from nina.core.locale.store import load as load_locale


def tokens_dir() -> Path:
    return Path(os.environ.get("TOKENS_DIR", "tokens"))


def data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data"))


def console_lang() -> str:
    return load_locale(data_dir()).lang
