from typing import Any

from nina.core.i18n import en, pt

_CATALOGS: dict[str, dict[str, str]] = {
    "en": en.STRINGS,
    "pt": pt.STRINGS,
}


def t(key: str, lang: str = "pt", **kwargs: Any) -> str:
    """Return the translated string for *key* in *lang*, formatted with kwargs.

    Falls back to English if the key is missing in the requested language,
    and returns the bare key if not found anywhere.
    """
    catalog = _CATALOGS.get(lang, _CATALOGS["pt"])
    template = catalog.get(key) or _CATALOGS["en"].get(key) or key
    return template.format(**kwargs) if kwargs else template
