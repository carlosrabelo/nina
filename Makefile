MAKEFLAGS += --no-print-directory

.DEFAULT_GOAL := help

.PHONY: clean dev-start dev-status dev-stop docker-auth-google docker-build \
        docker-logs docker-migrate docker-push docker-restart docker-start docker-stop \
        console fmt help lint quality run setup test

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
	@echo "make"
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*## "}{t=$$1;d=$$2;g="Other";if(t=="help")g="General";else if(t=="setup")g="Setup";else if(t=="run"||t=="console")g="Local";else if(t ~ /^dev-/)g="Dev";else if(t ~ /^docker-/)g="Docker";else if(t=="test"||t=="lint"||t=="fmt"||t=="quality"||t=="clean")g="Quality";items[g]=items[g] sprintf("  %-22s %s\n",t,d)}END{order[1]="General";order[2]="Setup";order[3]="Local";order[4]="Dev";order[5]="Docker";order[6]="Quality";order[7]="Other";for(i=1;i<=7;i++){g=order[i];if(items[g]!=""){printf("\n%s\n",g);printf("%s",items[g])}}}'

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

docker-start: ## Start docker compose stack (detached)
	NINA_IMAGE="$(TAG_COMMIT)" docker compose up -d --build

docker-stop: ## Stop docker compose stack
	docker compose down

docker-restart: docker-stop docker-start ## Restart docker compose stack (down + up)

docker-logs: ## Tail daemon container logs
	docker compose logs -f

docker-migrate: ## Run migrate_to_postgres.py inside the container
	docker compose run --rm -v ./scripts:/scripts nina python /scripts/migrate_to_postgres.py

docker-auth-google: ## Run Google OAuth flow inside the container
	docker compose run --rm -it nina python -m nina auth-google

# ── Run local CLI ─────────────────────────────────────────────────────────────

run: ## Run nina CLI locally (uses .env). Example: make run migrate to-postgres
	@ARGS="$(filter-out $@,$(MAKECMDGOALS))"; \
	if [ "$$ARGS" = "migrate to-postgres" ]; then \
		DATABASE_URL="$$DATABASE_URL_HOST" \
		DATA_DIR="$$DATA_DIR_HOST" \
		TOKENS_DIR="$$TOKENS_DIR_HOST" \
		SESSIONS_DIR="$$SESSIONS_DIR_HOST" \
		GOOGLE_CREDENTIALS_FILE="$$GOOGLE_CREDENTIALS_FILE_HOST" \
		.venv/bin/python scripts/migrate_to_postgres.py; \
	else \
		DATABASE_URL="$$DATABASE_URL_HOST" \
		DATA_DIR="$$DATA_DIR_HOST" \
		TOKENS_DIR="$$TOKENS_DIR_HOST" \
		SESSIONS_DIR="$$SESSIONS_DIR_HOST" \
		GOOGLE_CREDENTIALS_FILE="$$GOOGLE_CREDENTIALS_FILE_HOST" \
		.venv/bin/python -m nina $$ARGS; \
	fi

console: ## Open interactive console (requires daemon)
	@DATABASE_URL="$$DATABASE_URL_HOST" \
	DATA_DIR="$$DATA_DIR_HOST" \
	TOKENS_DIR="$$TOKENS_DIR_HOST" \
	SESSIONS_DIR="$$SESSIONS_DIR_HOST" \
	GOOGLE_CREDENTIALS_FILE="$$GOOGLE_CREDENTIALS_FILE_HOST" \
	.venv/bin/python -m nina console

# Swallow extra args as make "targets" (e.g. `make run migrate to-postgres`)
%:
	@:
