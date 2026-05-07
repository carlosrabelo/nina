#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Format (ruff)"
.venv/bin/ruff format nina/ tests/

echo "==> Lint (ruff)"
.venv/bin/ruff check nina/ tests/

echo "==> Typecheck (mypy)"
.venv/bin/mypy nina/
