# nina

Personal assistant CLI for managing Gmail, Google Calendar, and Telegram — built to be extended incrementally.

## Highlights

- **PostgreSQL** for runtime state (memos, actions, emails, calendar notification queue, presence/workdays/notifications/profile/locale in `kv_state`) — OAuth tokens, sessions, and Google credentials stay on disk
- Presence-aware account routing — track home/work/out/dnd and map each status to the right Google accounts (Gmail + Calendar)
- Interactive console and Telegram bot driven by a unified LLM intent router — one call classifies the domain and extracts entities
- **Calendar (read)** via natural language in Telegram/console — today/tomorrow/next N days, keyword search, free-busy gaps; **writes** (blocking a slot) use the separate `blocking` flow and `POST /schedule`
- Calendar blocking via free text ("I'm in a meeting for 1h") with full date resolution ("next Monday at 14:00")
- Memos and reminders via natural language ("remind me on Monday at 10h") — create, list, close, and dismiss from console or Telegram
- Calendar notifications via Telegram — reminders, new events, changes, cancellations
- Bilingual interface (English / Portuguese) — switch with `lang en` or `/lang en`
- Authenticate any number of Google accounts via OAuth — auto-discovered from saved tokens
- Query any LLM provider (Groq, OpenAI, Anthropic, Ollama) through a single LiteLLM interface
- Internal scheduler (APScheduler) plus HTTP slash commands for external integrations (MacroDroid, scripts) — no external cron required
- **Gmail label learning (per account):** **`nina gmail_label process`** fetches inbox mail, records headers in PostgreSQL, applies learned labels in Gmail, and can suggest new senders on Telegram from the daemon; optional **`--days`** and **`--max-per-account`** widen the Gmail query and raise the per-account fetch cap (up to 5000); messages already marked **`tagged_at`** in **`email_messages`** are skipped early (no header upsert); **`nina gmail_label infer-rules`** only adds new **`email_sender_rules`** from existing Gmail user labels (no inbox DB writes); both commands accept **`-v` / `--verbose`** for progress on stderr; **`nina gmail_label rules`** lists stored rules; teach labels via `/gmail_label` or `gmail_label` in `nina console`; **`/gmail_label dismiss-all`** clears all open suggestions; labels must start with **`@`** or **`!`**; ignored senders (**`nina gmail_label ignore …`**) are permanently excluded from suggestions.
- All secrets stay local: tokens, session files, and credentials on disk; application state lives in PostgreSQL

→ **[Command Reference (GUIDE.md)](GUIDE.md)** (full command table: [Full CLI command list](GUIDE.md#full-cli-command-list)) · **[HTTP API (API.md)](API.md)** / [API-PT.md](API-PT.md) · **[Skills (SKILL.md)](SKILL.md)** / [SKILL-PT.md](SKILL-PT.md) (behaviour domains under `nina/skills/`) · [AGENTS.md](AGENTS.md) (keep docs updated when the product changes)

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Layout](#project-layout)
- [Development](#development)
- [License](#license)

## Prerequisites

- **Python 3.12+**
- **Google Cloud project** with Gmail API and Google Calendar API enabled, and an OAuth 2.0 Desktop client — [console.cloud.google.com](https://console.cloud.google.com)
- **Telegram Bot token** from [@BotFather](https://t.me/BotFather) (needed for the bot interface)
- An **LLM API key** (Groq, OpenAI, Anthropic) or a local Ollama instance — needed for free-text commands

## Installation

```bash
git clone https://github.com/carlosrabelo/nina.git
cd nina
make setup
cp .env.example .env
# Edit .env — fill in the credentials for each service you want to use
```

## Usage

### 1. Authenticate Google accounts

```bash
.venv/bin/python -m nina auth-google   # opens browser — repeat for each account
.venv/bin/python -m nina status-google # ✓ you@gmail.com  ✓ work@gmail.com
```

The OAuth scope includes Google Calendar read/write — required for calendar blocking and notifications.

### 2. Configure the LLM

Add to `.env`:

```
LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=gsk_...
```

Other supported providers: `openai/gpt-4o-mini`, `anthropic/claude-haiku-4-5-20251001`, `ollama/llama3.2`.

```bash
.venv/bin/python -m nina llm-ping   # verify connectivity
```

### 3. Set up the Telegram bot

1. Talk to [@BotFather](https://t.me/BotFather) → `/newbot` → copy token to `TELEGRAM_BOT_TOKEN` in `.env`
2. Run `.venv/bin/python -m nina daemon`, then send `/start` to your bot
3. Copy the chat ID it replies with to `TELEGRAM_OWNER_ID` in `.env`

### 4. Start Nina

```bash
make dev-start  # daemon + console in a split tmux session (development — no Telegram)
# or
.venv/bin/python -m nina daemon   # production daemon (Telegram bot + HTTP API + scheduler)
make console     # console only (daemon must be running)
```

## Configuration

Copy [`.env.example`](.env.example) to `.env`. **Recommended:** set `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `POSTGRES_PORT` only; `nina` builds `DATABASE_URL` after loading `.env` (host `127.0.0.1` on the machine, host `postgres` inside a container). Set `DATABASE_URL` yourself only if you need extra URL options (e.g. `?sslmode=require`). Use **repo-relative paths** (`DATA_DIR=data/db`, …) for local CLI; inside Docker, `load_project_dotenv` adds a leading `/` to those same values when they are not already absolute (so `data/db` becomes `/data/db` on the `./data:/data` volume).

When you run **`nina`** or **`make run` / `make console`**, Python loads the nearest `.env` (`load_project_dotenv` in `nina/cli/_env.py`). There are no separate `*_HOST` variables.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_PORT` | — | **Primary:** Postgres credentials; `DATABASE_URL` is derived when unset (see above). |
| `POSTGRES_HOST` | — | Optional DB hostname override (otherwise `127.0.0.1` on the host, `postgres` in Docker). |
| `DATABASE_URL` | (built from `POSTGRES_*`) | Optional explicit PostgreSQL URL if you need non-default query params. |
| `NINA_IMAGE` | (see `.env.example`) | Image for Compose service `nina`; `make docker-start` overrides with `REGISTRY/IMAGE:<git sha>` and `--build` |
| `GOOGLE_CREDENTIALS_FILE`, `TOKENS_DIR`, `SESSIONS_DIR`, `DATA_DIR` | — | Paths: repo-relative on the host; in Docker, a leading `/` is added when the value is not already absolute (see above). |
| `NINA_HTTP_HOST` | `0.0.0.0` | Host interface to bind/publish the HTTP port |
| `NINA_HTTP_PORT` | `8765` | HTTP port |
| `NINA_API_KEY` | — | If set, protects HTTP API via header `X-Api-Key` |
| `TZ` / `PGTZ` | — | Timezone for containers and libpq-friendly Postgres client TZ |
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather |
| `TELEGRAM_OWNER_ID` | — | Your personal Telegram chat ID (bot only responds to this) |
| `LLM_MODEL` | `groq/llama-3.3-70b-versatile` | LiteLLM model string: `<provider>/<model>` |
| `GROQ_API_KEY` | — | Groq API key (required when using Groq) |
| `OPENAI_API_KEY` | — | OpenAI API key (required when using OpenAI) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (required when using Anthropic) |
| `LLM_TEMPERATURE` | `0.3` | Sampling temperature |
| `LLM_MAX_TOKENS` | `1024` | Maximum tokens in the response |

## Project Layout

```
nina/
    __main__.py              # python -m nina entry point
    errors.py                # shared exceptions
    cli/                     # CLI parser + command handlers (auth, status, daemon,
                             # console, gmail, calendar, tg, llm)
    tasks/
        email_process.py         # inbox ingest, apply rules, Telegram suggestions
        email_infer_rules.py     # scan Gmail user labels → insert sender rules
    skills/
        memo/                # memo creation, listing, and reminder management
        presence/            # presence status tracking
        workdays/            # work schedule and timezone
        calendar/            # execute.py (read), blocking (write), interpreter, schedule parser
        notifications/       # notification config and state
        profile/             # Google account mapping per presence
        activity_log/        # past activity logging to Google Calendar
        gmail_label/         # teach/dismiss labels, ignored senders, execute + interpreter
    integrations/
        google/
            auth.py          # Google OAuth flow, token caching, auto-discovery
            gmail/client.py
            calendar/client.py  # CalendarClient (list, create events)
        telegram/
            bot.py               # app factory, slash commands, batch runner
            command_registry.py  # /setMyCommands + bot_lang(ctx)
            constants.py         # MAX_MSG
            free_text_handler.py # natural language + LLM router (non-command messages)
            offset_store.py        # batch getUpdates offset persistence
    core/
        intent/
            router.py          # unified LLM router (4 layers)
            local_router.py    # local pattern matching — zero LLM
        nlp/                   # local date/time/duration parser
        store/               # PostgreSQL store (memos, actions, emails, events) + kv_state
        llm/                 # LLMClient — LiteLLM wrapper
        i18n/                # bilingual strings (en / pt)
        locale/              # locale config (language preference)
        scheduler/
            jobs/
                calendar_notifications.py  # reminders + change detection (every 5 min)
        daemon/
            runner.py        # daemon with APScheduler + HTTP server
            http.py          # HTTP API (presence, workdays, schedule, notifications)
            client.py        # console → daemon HTTP client
        console/
            runner.py              # interactive REPL (cmd.Cmd)
            paths.py               # DATA_DIR, TOKENS_DIR, console language
            intent_executors.py    # memo / notifications / activity_log → print
            freeform_dispatch.py   # natural language + LLM router for unknown lines
scripts/                     # e.g. migrate_to_postgres.py (legacy SQLite/JSON → Postgres)
.make/                       # setup.sh, test.sh, lint.sh, quality.sh, clean.sh, dev.sh
credentials/                 # credentials.json (git-ignored)
tokens/                      # OAuth tokens (git-ignored)
tests/                       # pytest test suite
```

## Development

```bash
make help       # list make targets and nina CLI commands
make setup      # create .venv and install dependencies
make test       # run all tests
make lint       # lint with ruff
make fmt        # format code with ruff
make quality    # fmt + lint + typecheck (mypy) in one shot
.venv/bin/python -m nina typecheck   # mypy on the nina package only
make dev-start  # start daemon + console in tmux (no Telegram)
make console    # open console (daemon must be running)
make run …      # run CLI with .env + host paths (e.g. `make run migrate to-postgres`)
make docker-start   # compose up with commit-tagged image + build
make docker-stop    # compose down
make docker-restart # docker-stop then docker-start
make docker-migrate # one-off migration script in container (mounts ./scripts)
```

Contributor note: keep user-facing docs in sync — see [AGENTS.md](AGENTS.md).

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
