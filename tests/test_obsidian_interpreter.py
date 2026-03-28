# tests/test_obsidian_interpreter.py
"""Tests for the Obsidian intent interpreter."""

from nina.obsidian.interpreter import try_action


class TestTryAction:
    def test_sync_pt(self) -> None:
        result = try_action("sincroniza o obsidian", "pt")
        assert result is not None
        assert result.action == "sync"

    def test_sync_vault_pt(self) -> None:
        result = try_action("atualiza o vault", "pt")
        assert result is not None
        assert result.action == "sync"

    def test_sync_en(self) -> None:
        result = try_action("sync obsidian", "en")
        assert result is not None
        assert result.action == "sync"

    def test_no_keyword_returns_none(self) -> None:
        assert try_action("atualiza o sistema", "pt") is None
        assert try_action("sync my memos", "en") is None
