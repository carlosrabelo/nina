MAKEFLAGS += --no-print-directory

.DEFAULT_GOAL := help

.PHONY: clean dev-start dev-status dev-stop docker-auth-google docker-build \
        docker-down docker-logs docker-push docker-up fmt help lint quality \
        run setup test

# Load local environment variables (if .env exists)
-include .env
export

# ── Variables ─────────────────────────────────────────────────────────────────

IMAGE      ?= nina
REGISTRY   ?= carlosrabelo
COMMIT     := $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)
TAG_COMMIT := $(REGISTRY)/$(IMAGE):$(COMMIT)
TAG_LATEST := $(REGISTRY)/$(IMAGE):latest

PY_SOURCES := nina/

# ── Help ──────────────────────────────────────────────────────────────────────

help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*## "} {printf "  %-22s %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────

setup: ## Create .venv and install dependencies
	@./.make/setup.sh

# ── Development ───────────────────────────────────────────────────────────────

test: ## Run all tests
	@./.make/test.sh

lint: ## Lint with ruff
	@./.make/lint.sh

fmt: ## Format code with ruff
	@.venv/bin/ruff format $(PY_SOURCES) tests/

quality: ## Run fmt, lint, and typecheck (mypy)
	@./.make/quality.sh

clean: ## Remove build artifacts and __pycache__
	@./.make/clean.sh

# ── Dev session ───────────────────────────────────────────────────────────────

dev-start: ## Launch daemon + console in a tmux session (reattaches if running)
	@./.make/dev.sh

dev-status: ## Show whether the dev tmux session and daemon are running
	@./.make/dev-status.sh

dev-stop: ## Kill the dev tmux session and any stray daemon process
	@./.make/dev-stop.sh

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build: ## Build the Docker image and tag REGISTRY/IMAGE
	docker build --network=host -t $(TAG_COMMIT) -t $(TAG_LATEST) .

docker-push: docker-build ## Build and push image to Docker Hub
	docker push $(TAG_COMMIT)
	docker push $(TAG_LATEST)

docker-up: ## Start daemon container (detached)
	docker compose up -d

docker-down: ## Stop daemon container
	docker compose down

docker-logs: ## Tail daemon container logs
	docker compose logs -f

docker-auth-google: ## Run Google OAuth flow inside the container
	docker compose run --rm -it nina python -m nina auth-google

# ── Run local CLI ─────────────────────────────────────────────────────────────

run: ## Run nina CLI locally (uses .env). Example: make run migrate to-postgres
	@.venv/bin/python -m nina $(filter-out $@,$(MAKECMDGOALS))

# Swallow extra args as make "targets" (e.g. `make run migrate to-postgres`)
%:
	@:
