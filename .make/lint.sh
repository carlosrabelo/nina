#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

"$ROOT_DIR/.venv/bin/ruff" check "$ROOT_DIR/nina/" "$ROOT_DIR/tests/"
