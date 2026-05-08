from pathlib import Path

from nina.core.locale.models import DEFAULT, LocaleConfig
from nina.core.store.db import open_db
from nina.core.store.kv import ensure_json, get_json, set_json

_KEY = "locale"


def load(data_dir: Path) -> LocaleConfig:
    conn = open_db(data_dir)
    try:
        data = get_json(conn, _KEY)
    finally:
        conn.close()
    if not data:
        return LocaleConfig()
    return LocaleConfig(lang=data.get("lang", DEFAULT))


def save(config: LocaleConfig, data_dir: Path) -> None:
    conn = open_db(data_dir)
    try:
        set_json(conn, _KEY, {"lang": config.lang})
    finally:
        conn.close()


def ensure_default(data_dir: Path) -> None:
    conn = open_db(data_dir)
    try:
        ensure_json(conn, _KEY, {"lang": DEFAULT})
    finally:
        conn.close()
