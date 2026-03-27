MAKEFLAGS += --no-print-directory

PY_FILES  := $(wildcard *.py)
ACCOUNT   ?=
LIMIT     ?=
CAL       ?=

_py       := .venv/bin/python nina.py
_account  := $(if $(ACCOUNT),--account $(ACCOUNT),)
_limit    := $(if $(LIMIT),--limit $(LIMIT),)
_cal      := $(if $(CAL),--calendar $(CAL),)

.PHONY: help
.PHONY: setup test lint fmt typecheck clean
.PHONY: auth status
.PHONY: gmail-latest gmail-unread gmail-search
.PHONY: cal-calendars cal-events
.PHONY: tg-bot tg-bot-setup tg-auth tg-status tg-dialogs tg-messages tg-send

help:
	@echo "Usage: make <target> [ACCOUNT=email] [LIMIT=n]"
	@echo ""
	@echo "Setup"
	@echo "  setup           Create .venv and install dependencies"
	@echo ""
	@echo "Development"
	@echo "  test            Run all tests"
	@echo "  lint            Lint with ruff"
	@echo "  fmt             Format code with ruff"
	@echo "  typecheck       Type-check with mypy"
	@echo "  clean           Remove build artifacts and __pycache__"
	@echo ""
	@echo "Accounts"
	@echo "  auth            Add an account via Google OAuth (opens browser)"
	@echo "  status          Show auth status for all accounts"
	@echo ""
	@echo "Gmail                                  [ACCOUNT=] [LIMIT=]"
	@echo "  gmail-latest    Headers of the most recent emails"
	@echo "  gmail-unread    List unread messages"
	@echo "  gmail-search    Search messages  (QUERY= required)"
	@echo ""
	@echo "Calendar                               [ACCOUNT=] [LIMIT=] [CAL=]"
	@echo "  cal-calendars   List all calendars in the account"
	@echo "  cal-events      List upcoming events  (CAL= calendar id, default: primary)"
	@echo ""
	@echo "Telegram                               [LIMIT=]"
	@echo "  tg-bot          Process pending bot commands (batch mode)"
	@echo "  tg-bot-setup    Find your TELEGRAM_OWNER_ID (first-time setup)"
	@echo "  tg-auth         Authenticate with Telegram (phone verification)"
	@echo "  tg-status       Show Telegram authentication status"
	@echo "  tg-dialogs      List recent chats/groups/channels"
	@echo "  tg-messages     Show messages from a chat  (CHAT= required)"
	@echo "  tg-send         Send a message  (CHAT= and TEXT= required)"

# ── Setup ────────────────────────────────────────────────────────────────────

setup:
	./make/setup.sh

# ── Development ──────────────────────────────────────────────────────────────

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

# ── Accounts ─────────────────────────────────────────────────────────────────

auth:
	$(_py) auth

status:
	$(_py) status

# ── Gmail ────────────────────────────────────────────────────────────────────

gmail-latest:
	$(_py) latest $(_account) $(_limit)

gmail-unread:
	$(_py) unread $(_account) $(_limit)

gmail-search:
	$(_py) search "$(QUERY)" $(_account) $(_limit)

# ── Calendar ─────────────────────────────────────────────────────────────────

cal-calendars:
	$(_py) calendars $(_account)

cal-events:
	$(_py) events $(_account) $(_limit) $(_cal)

# ── Telegram ─────────────────────────────────────────────────────────────────

tg-bot:
	$(_py) tg-bot

tg-bot-setup:
	$(_py) tg-bot-setup

tg-auth:
	$(_py) tg-auth $(if $(PHONE),--phone $(PHONE),)

tg-status:
	$(_py) tg-status

tg-dialogs:
	$(_py) tg-dialogs $(_limit)

tg-messages:
	$(_py) tg-messages $(CHAT) $(_limit)

tg-send:
	$(_py) tg-send $(CHAT) "$(TEXT)"
