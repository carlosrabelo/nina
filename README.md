# nina

Personal assistant CLI for managing Gmail, Google Calendar, and Telegram — built to be extended incrementally.

## Highlights

- Presence-aware account routing — track home/work/out/dnd and map each status to the right Google accounts (Gmail + Calendar)
- Interactive console and Telegram bot driven by a unified LLM intent router — one call classifies the domain and extracts entities
- Calendar blocking via free text ("I'm in a meeting for 1h") with full date resolution ("next Monday at 14:00")
- Memos and reminders via natural language ("remind me on Monday at 10h") — create, list, close, and dismiss from console or Telegram
- Calendar notifications via Telegram — reminders, new events, changes, cancellations
- Bilingual interface (English / Portuguese) — switch with `lang en` or `/lang en`
- Authenticate any number of Google accounts via OAuth — auto-discovered from saved tokens
- Query any LLM provider (Groq, OpenAI, Anthropic, Ollama) through a single LiteLLM interface
- Internal scheduler (APScheduler) plus HTTP slash commands for external integrations (MacroDroid, scripts) — no external cron required
- All secrets stay local: tokens, session files, and credentials are git-ignored

→ **[Command Reference (GUIDE.md)](GUIDE.md)**

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
.venv/bin/python -m nina console  # console only (daemon must be running)
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_CREDENTIALS_FILE` | `credentials/credentials.json` | OAuth client credentials downloaded from Google Cloud Console |
| `TOKENS_DIR` | `tokens` | Directory for all token and session files (git-ignored) |
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
    skills/
        memo/                # memo creation, listing, and reminder management
        presence/            # presence status tracking
        workdays/            # work schedule and timezone
        calendar/            # LLM blocking, natural language interpreter, schedule parser
        notifications/       # notification config and state
        profile/             # Google account mapping per presence
        activity_log/        # past activity logging to Google Calendar
    integrations/
        google/
            auth.py          # Google OAuth flow, token caching, auto-discovery
            gmail/client.py
            calendar/client.py  # CalendarClient (list, create events)
        telegram/bot.py      # Telegram Bot (daemon mode)
    core/
        intent/
            router.py          # unified LLM router (4 layers)
            local_router.py    # local pattern matching — zero LLM
        nlp/                   # local date/time/duration parser
        store/               # SQLite store (memos, actions, emails, events)
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
        console/runner.py    # interactive REPL
.make/                       # setup.sh, test.sh, lint.sh, quality.sh, clean.sh, dev.sh
credentials/                 # credentials.json (git-ignored)
tokens/                      # OAuth tokens, locale, profile, workdays, notifications (git-ignored)
tests/                       # pytest test suite (302+ tests)
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
```

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
