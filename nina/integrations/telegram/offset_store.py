"""Persisted offset for Telegram getUpdates (batch mode)."""

from pathlib import Path


def _offset_file(sessions_dir: Path) -> Path:
    return sessions_dir / "bot_offset.txt"


def load_offset(sessions_dir: Path) -> int:
    """Return the stored update offset, or 0 if not yet set."""
    f = _offset_file(sessions_dir)
    return int(f.read_text().strip()) if f.exists() else 0


def save_offset(sessions_dir: Path, offset: int) -> None:
    """Persist the next offset so the next run skips already-processed updates."""
    sessions_dir.mkdir(parents=True, exist_ok=True)
    _offset_file(sessions_dir).write_text(str(offset))
