#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -d "$ROOT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$ROOT_DIR/.venv"
fi

echo "Installing dependencies..."
"$ROOT_DIR/.venv/bin/pip" install "$ROOT_DIR[dev]" --quiet
echo "Setup complete."

if [ ! -f "$ROOT_DIR/.env" ]; then
    echo ""
    echo "Next steps:"
    echo "  1. cp .env.example .env"
    echo "  2. Edit .env — set GMAIL_ACCOUNTS and GOOGLE_CREDENTIALS_FILE"
    echo "  3. make auth-all"
fi
