#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT_DIR/.venv/bin/python"

# Called via: make auth ACCOUNT=email@gmail.com
# Called via: make auth-all  (passes --all)

if [ "${1:-}" = "--all" ]; then
    echo "Authenticating all accounts from .env ..."
    "$PY" "$ROOT_DIR/nina.py" auth
else
    if [ -z "${ACCOUNT:-}" ]; then
        echo "Usage: make auth ACCOUNT=email@gmail.com"
        echo "       make auth-all"
        exit 1
    fi
    echo "Authenticating $ACCOUNT ..."
    "$PY" "$ROOT_DIR/nina.py" auth --account "$ACCOUNT"
fi
