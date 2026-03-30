# tests/test_i18n.py
"""Tests for the i18n translation helper."""

import pytest

from nina.core.i18n import t


class TestTranslation:
    def test_returns_portuguese_by_default(self) -> None:
        assert t("unread.none") == "Nenhum email não lido."

    def test_returns_english_when_lang_en(self) -> None:
        assert t("unread.none", "en") == "No unread emails."

    def test_formats_kwargs(self) -> None:
        result = t("unread.error", "pt", error="boom")
        assert result == "Erro: boom"

    def test_formats_kwargs_en(self) -> None:
        result = t("unread.error", "en", error="boom")
        assert result == "Error: boom"

    def test_falls_back_to_default_lang_for_unknown_lang(self) -> None:
        # Unknown language code → falls back to the default catalog (pt)
        result = t("unread.none", "xx")
        assert result == "Nenhum email não lido."

    def test_returns_key_when_not_found_anywhere(self) -> None:
        result = t("nonexistent.key", "pt")
        assert result == "nonexistent.key"

    def test_presence_labels_pt(self) -> None:
        assert t("presence.label.home", "pt") == "em casa"
        assert t("presence.label.office", "pt") == "no escritório"
        assert t("presence.label.out", "pt") == "na rua / em movimento"
        assert t("presence.label.dnd", "pt") == "não perturbe"

    def test_presence_labels_en(self) -> None:
        assert t("presence.label.home", "en") == "at home"
        assert t("presence.label.office", "en") == "at the office"

    def test_context_labels_pt(self) -> None:
        assert t("context.label.dnd", "pt") == "foco total"
        assert t("context.label.home_office", "pt") == "home office"

    def test_context_labels_en(self) -> None:
        assert t("context.label.dnd", "en") == "deep focus"
        assert t("context.label.home_office", "en") == "home office"

    def test_day_names_pt(self) -> None:
        assert t("day.0", "pt") == "Segunda"
        assert t("day.6", "pt") == "Domingo"

    def test_day_names_en(self) -> None:
        assert t("day.0", "en") == "Monday"
        assert t("day.6", "en") == "Sunday"

    def test_dialogs_unread_pt(self) -> None:
        result = t("dialogs.unread", "pt", count=3)
        assert result == " (3 não lidas)"

    def test_dialogs_unread_en(self) -> None:
        result = t("dialogs.unread", "en", count=3)
        assert result == " (3 unread)"
