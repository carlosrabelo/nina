"""Normalize Gmail From headers to a lowercase email address."""

from __future__ import annotations

import re
from email.utils import parseaddr


def normalize_sender(from_header: str) -> str:
    """Return best-effort lowercase email from a From header."""
    raw = (from_header or "").strip()
    if not raw:
        return ""

    _name, addr = parseaddr(raw)
    addr = addr.strip().lower()
    if addr and "@" in addr:
        return addr

    m = re.search(r"<([^>]+@[^>]+)>", raw)
    if m:
        return m.group(1).strip().lower()

    m = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", raw)
    if m:
        return m.group(0).lower()

    return raw[:512].lower()
