# tests/test_locale.py
"""Tests for the locale domain."""

from pathlib import Path

from nina.core.locale.models import LocaleConfig
from nina.core.locale.store import load, save


class TestLocaleStore:
    def test_load_returns_default_when_no_file(self, tmp_path: Path) -> None:
        config = load(tmp_path)
        assert config.lang == "pt"

    def test_save_then_load(self, tmp_path: Path) -> None:
        save(LocaleConfig(lang="en"), tmp_path)
        assert load(tmp_path).lang == "en"

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "dir"
        save(LocaleConfig(lang="pt"), nested)
        assert load(nested).lang == "pt"

    def test_save_overwrites(self, tmp_path: Path) -> None:
        save(LocaleConfig(lang="pt"), tmp_path)
        save(LocaleConfig(lang="en"), tmp_path)
        assert load(tmp_path).lang == "en"

    def test_load_unknown_lang_key_falls_back_to_default(self, tmp_path: Path) -> None:
        (tmp_path / "locale.json").write_text("{}")
        config = load(tmp_path)
        assert config.lang == "pt"
