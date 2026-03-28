# nina/obsidian/__init__.py
"""Obsidian vault writer — resolves vault path and writes markdown files."""

import os
from pathlib import Path


def vault_path() -> Path | None:
    """Return the configured vault path, or None if not set."""
    raw = os.environ.get("OBSIDIAN_VAULT_PATH", "")
    if not raw:
        return None
    return Path(raw).expanduser()


def write_page(filename: str, content: str, subfolder: str = "") -> Path | None:
    """Write *content* to *filename* inside the vault.

    Returns the written path, or None if OBSIDIAN_VAULT_PATH is not configured.
    Intermediate directories are created automatically.
    """
    root = vault_path()
    if root is None:
        return None

    target = root / subfolder / filename if subfolder else root / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_text(encoding="utf-8") == content:
        return target
    target.write_text(content, encoding="utf-8")
    return target


def ensure_folders() -> None:
    """Create the standard vault folder structure if it doesn't exist."""
    root = vault_path()
    if root is None:
        return
    for folder in ("daily", "digest", "captured", "permanent"):
        (root / folder).mkdir(parents=True, exist_ok=True)
