MAKEFLAGS += --no-print-directory

ACCOUNT   ?=
LIMIT     ?=
CAL       ?=
IMAGE     ?= nina

_py       := .venv/bin/python -m nina
_play     := .venv/bin/python -m nina_play
_account  := $(if $(ACCOUNT),--account $(ACCOUNT),)
_limit    := $(if $(LIMIT),--limit $(LIMIT),)
_cal      := $(if $(CAL),--calendar $(CAL),)

.PHONY: help
.PHONY: setup test lint fmt typecheck clean
.PHONY: auth-google auth-telegram status-google status-telegram console daemon dev
.PHONY: docker-build docker-up docker-down docker-logs docker-auth-google
.PHONY: play-gmail-latest play-gmail-unread play-gmail-search
.PHONY: play-cal-calendars play-cal-events
.PHONY: play-tg-bot play-tg-bot-setup play-tg-dialogs play-tg-messages play-tg-send
.PHONY: play-llm-ping play-llm-demo

help:
	@echo "Usage: make <target> [ACCOUNT=email] [LIMIT=n]"
	@echo ""
	@echo "Setup"
	@echo "  setup                Create .venv and install dependencies"
	@echo ""
	@echo "Development"
	@echo "  test                 Run all tests"
	@echo "  lint                 Lint with ruff"
	@echo "  fmt                  Format code with ruff"
	@echo "  typecheck            Type-check with mypy"
	@echo "  clean                Remove build artifacts and __pycache__"
	@echo ""
	@echo "Nina"
	@echo "  auth-google          Add a Google account via OAuth (opens browser)"
	@echo "  auth-telegram        Authenticate with Telegram (phone verification)"
	@echo "  status-google        Show Google auth status for all accounts"
	@echo "  status-telegram      Show Telegram authentication status"
	@echo "  console              Open interactive console (requires daemon)"
	@echo "  daemon               Start Nina in daemon mode (scheduler + HTTP)"
	@echo "  dev                  Launch daemon + console in a tmux session"
	@echo ""
	@echo "Docker"
	@echo "  docker-build         Build the Docker image"
	@echo "  docker-up            Start daemon container (detached)"
	@echo "  docker-down          Stop daemon container"
	@echo "  docker-logs          Tail daemon container logs"
	@echo "  docker-auth-google   Run Google OAuth flow inside the container"
	@echo ""
	@echo "Nina Play — exploration                [ACCOUNT=] [LIMIT=] [CAL=]"
	@echo "  play-gmail-latest    Headers of the most recent emails"
	@echo "  play-gmail-unread    List unread messages"
	@echo "  play-gmail-search    Search messages  (QUERY= required)"
	@echo "  play-cal-calendars   List all calendars in the account"
	@echo "  play-cal-events      List upcoming events  (CAL= calendar id)"
	@echo "  play-tg-bot          Process pending bot commands (batch mode)"
	@echo "  play-tg-bot-setup    Find your TELEGRAM_OWNER_ID (first-time setup)"
	@echo "  play-tg-dialogs      List recent chats/groups/channels"
	@echo "  play-tg-messages     Show messages from a chat  (CHAT= required)"
	@echo "  play-tg-send         Send a message  (CHAT= and TEXT= required)"
	@echo "  play-llm-ping        Verify LLM connectivity and auth"
	@echo "  play-llm-demo        Run digest demo with real/simulated data"

# ── Setup ─────────────────────────────────────────────────────────────────────

setup:
	./make/setup.sh

# ── Development ───────────────────────────────────────────────────────────────

test:
	./make/test.sh

lint:
	./make/lint.sh

fmt:
	.venv/bin/ruff format nina/ nina_play/ tests/

typecheck:
	.venv/bin/mypy nina/ nina_play/

clean:
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# ── Nina ──────────────────────────────────────────────────────────────────────

auth-google:
	$(_py) auth google

auth-telegram:
	$(_py) auth telegram $(if $(PHONE),--phone $(PHONE),)

status-google:
	$(_py) status google

status-telegram:
	$(_py) status telegram

console:
	$(_py) console

daemon:
	$(_py) daemon

dev:
	@if tmux has-session -t nina 2>/dev/null; then \
		tmux attach-session -t nina; \
	else \
		tmux new-session -d -s nina -x 220 -y 50; \
		tmux send-keys -t nina:0.0 "cd $(CURDIR) && $(_py) daemon --dev" Enter; \
		tmux split-window -v -t nina:0.0; \
		tmux send-keys -t nina:0.1 "cd $(CURDIR) && sleep 2 && make console" Enter; \
		tmux select-pane -t nina:0.1; \
		tmux attach-session -t nina; \
	fi

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-auth-google:
	docker compose run --rm -it nina python -m nina auth google

# ── Nina Play — Gmail ─────────────────────────────────────────────────────────

play-gmail-latest:
	$(_play) latest $(_account) $(_limit)

play-gmail-unread:
	$(_play) unread $(_account) $(_limit)

play-gmail-search:
	$(_play) search "$(QUERY)" $(_account) $(_limit)

# ── Nina Play — Calendar ──────────────────────────────────────────────────────

play-cal-calendars:
	$(_play) calendars $(_account)

play-cal-events:
	$(_play) events $(_account) $(_limit) $(_cal)

# ── Nina Play — Telegram ──────────────────────────────────────────────────────

play-tg-bot:
	$(_play) tg-bot

play-tg-bot-setup:
	$(_play) tg-bot-setup

play-tg-dialogs:
	$(_play) tg-dialogs $(_limit)

play-tg-messages:
	$(_play) tg-messages $(CHAT) $(_limit)

play-tg-send:
	$(_play) tg-send $(CHAT) "$(TEXT)"

# ── Nina Play — LLM ───────────────────────────────────────────────────────────

play-llm-ping:
	$(_play) llm-ping

play-llm-demo:
	.venv/bin/python -m nina.demos.digest
