from dataclasses import dataclass

SUPPORTED: set[str] = {"en", "pt"}
DEFAULT = "pt"


@dataclass
class LocaleConfig:
    lang: str = DEFAULT
