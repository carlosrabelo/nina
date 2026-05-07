#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

rm -rf dist/ build/ ./*.egg-info
find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
find . -type f -name "*.pyc" -not -path "./.venv/*" -delete
