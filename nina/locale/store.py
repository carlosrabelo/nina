import json
from pathlib import Path

from nina.locale.models import DEFAULT, LocaleConfig

_FILENAME = "locale.json"


def load(data_dir: Path) -> LocaleConfig:
    path = data_dir / _FILENAME
    if not path.exists():
        return LocaleConfig()
    data = json.loads(path.read_text())
    return LocaleConfig(lang=data.get("lang", DEFAULT))


def save(config: LocaleConfig, data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / _FILENAME).write_text(json.dumps({"lang": config.lang}, indent=2))
