import json
from pathlib import Path

from nina.locale.models import DEFAULT, LocaleConfig

_FILENAME = "locale.json"


def load(tokens_dir: Path) -> LocaleConfig:
    path = tokens_dir / _FILENAME
    if not path.exists():
        return LocaleConfig()
    data = json.loads(path.read_text())
    return LocaleConfig(lang=data.get("lang", DEFAULT))


def save(config: LocaleConfig, tokens_dir: Path) -> None:
    tokens_dir.mkdir(parents=True, exist_ok=True)
    (tokens_dir / _FILENAME).write_text(json.dumps({"lang": config.lang}, indent=2))
