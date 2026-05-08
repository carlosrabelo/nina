from __future__ import annotations

import os

REQUIRED_ENV_VARS = ("DATABASE_URL", "NINA_HTTP_HOST", "NINA_HTTP_PORT")


def missing_required_env() -> list[str]:
    missing: list[str] = []
    for key in REQUIRED_ENV_VARS:
        val = os.environ.get(key, "")
        if not val or not val.strip():
            missing.append(key)
    return missing


def exit_if_missing_required_env() -> None:
    missing = missing_required_env()
    if not missing:
        return
    print(f"missing required env (noop): {', '.join(missing)}")
    raise SystemExit(0)

