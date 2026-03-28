# nina/obsidian/open_page.py
"""Renders open.md — list of open memos and actions."""

import sqlite3
from datetime import datetime, timezone

from nina.store.repos import memo as memo_repo


def render(conn: sqlite3.Connection, lang: str = "en") -> str:
    """Return the full markdown content for open.md."""
    memos = memo_repo.list_open(conn)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if lang == "pt":
        title = "# Abertos"
        updated_label = f"_Atualizado: {now}_"
        empty_label = "_Nenhum memo aberto._"
        memo_section = "## Memos"
        due_label = "Vence"
    else:
        title = "# Open"
        updated_label = f"_Updated: {now}_"
        empty_label = "_No open memos._"
        memo_section = "## Memos"
        due_label = "Due"

    lines = [title, "", updated_label, ""]

    lines += [memo_section, ""]
    if not memos:
        lines += [empty_label, ""]
    else:
        for m in memos:
            due = f" — {due_label}: {m.due_date}" if m.due_date else ""
            source_tag = " 🎤" if m.source == "voice" else ""
            short_id = m.id[:8]
            lines.append(f"- [ ] {m.text}{due}{source_tag} `{short_id}`")
        lines.append("")

    return "\n".join(lines)
