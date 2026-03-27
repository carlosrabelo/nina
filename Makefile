MAKEFLAGS += --no-print-directory

PY_FILES := $(wildcard *.py)

.PHONY: setup test lint fmt typecheck clean auth status latest help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup"
	@echo "  setup        Create .venv and install dependencies"
	@echo ""
	@echo "Development"
	@echo "  test         Run tests"
	@echo "  lint         Lint with ruff"
	@echo "  fmt          Format code with ruff"
	@echo "  typecheck    Type-check with mypy"
	@echo "  clean        Remove build artifacts and __pycache__"
	@echo ""
	@echo "Gmail"
	@echo "  auth         Add an account via Google OAuth (opens browser)"
	@echo "  status       Show auth status for all accounts"
	@echo "  latest       Show headers of the most recent emails"

setup:
	./make/setup.sh

test:
	./make/test.sh

lint:
	./make/lint.sh

fmt:
	.venv/bin/ruff format $(PY_FILES) tests/

typecheck:
	.venv/bin/mypy $(PY_FILES)

clean:
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

auth:
	.venv/bin/python nina.py auth

status:
	.venv/bin/python nina.py status

latest:
	.venv/bin/python nina.py latest $(if $(ACCOUNT),--account $(ACCOUNT),)
