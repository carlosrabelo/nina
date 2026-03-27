# nina

Personal assistant CLI for managing Gmail, Google Calendar, and Telegram — built to be extended incrementally.

## Highlights

- Authenticate any number of Gmail accounts via Google OAuth — no manual email list required
- Auto-discovers authenticated accounts from saved tokens on startup
- List unread messages, search, and show recent email headers across all Gmail accounts
- List upcoming Calendar events, filter by calendar ID
- Read and send Telegram messages acting as your personal account (Telethon)
- Receive commands via a Telegram Bot in batch mode — no persistent loop required
- Query any LLM provider (Groq, OpenAI, Anthropic, Ollama) through a single LiteLLM interface — switch providers with one `.env` change
- Internal scheduler (APScheduler) to run jobs on a defined schedule — no external cron required
- Token refresh handled automatically for Google; re-auth only when truly needed
- All secrets stay local: tokens, session files, and credentials are git-ignored

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage — Google](#usage--google)
- [Usage — Telegram User Client](#usage--telegram-user-client)
- [Usage — Telegram Bot](#usage--telegram-bot)
- [Usage — LLM](#usage--llm)
- [Usage — Scheduler](#usage--scheduler)
- [Project Layout](#project-layout)
- [Development](#development)
- [License](#license)

## Prerequisites

- **Python 3.12+**
- **Google Cloud project** with Gmail API and Google Calendar API enabled, and an OAuth 2.0 Desktop client — [console.cloud.google.com](https://console.cloud.google.com)
- **Telegram API credentials** (`api_id` / `api_hash`) from [my.telegram.org](https://my.telegram.org) → API Development Tools
- **Telegram Bot token** from [@BotFather](https://t.me/BotFather) (only needed to receive commands via bot)

## Installation

```bash
git clone https://github.com/carlosrabelo/nina.git
cd nina
make setup
cp .env.example .env
# Edit .env — fill in the credentials for each service you want to use
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_CREDENTIALS_FILE` | `credentials/credentials.json` | OAuth client credentials downloaded from Google Cloud Console |
| `TOKENS_DIR` | `tokens` | Directory for all token and session files (git-ignored) |
| `TELEGRAM_API_ID` | — | Telegram MTProto API id from my.telegram.org |
| `TELEGRAM_API_HASH` | — | Telegram MTProto API hash from my.telegram.org |
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather |
| `TELEGRAM_OWNER_ID` | — | Your personal Telegram chat ID (bot only responds to this) |
| `LLM_MODEL` | `groq/llama-3.3-70b-versatile` | LiteLLM model string: `<provider>/<model>` |
| `GROQ_API_KEY` | — | Groq API key (required when using Groq) |
| `OPENAI_API_KEY` | — | OpenAI API key (required when using OpenAI) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (required when using Anthropic) |
| `LLM_TEMPERATURE` | `0.3` | Sampling temperature |
| `LLM_MAX_TOKENS` | `1024` | Maximum tokens in the response |

## Usage — Google

### Authenticate a Google account

Run once per account — opens the browser, you pick the Google account:

```bash
make auth
```

Repeat for each account. Nina discovers all authenticated accounts automatically.

### Check status

```bash
make status
# ✓  you@gmail.com
# ✓  work@gmail.com
```

### Gmail

```bash
make gmail-latest                               # recent email headers, all accounts
make gmail-latest ACCOUNT=you@gmail.com        # single account
make gmail-unread LIMIT=5                       # unread messages
make gmail-search QUERY="subject:invoice is:unread"
make gmail-search QUERY="from:boss" ACCOUNT=work@gmail.com
```

### Calendar

```bash
make cal-calendars                              # list all calendars with their IDs
make cal-events                                 # upcoming events (primary calendar)
make cal-events LIMIT=5
make cal-events CAL=abc123@group.calendar.google.com   # specific calendar
make cal-events ACCOUNT=work@gmail.com CAL=abc123@group.calendar.google.com
```

### Revoke a Google account

```bash
./nina.py revoke you@gmail.com
```

## Usage — Telegram User Client

The user client lets Nina read and send messages **as you** — acting on your personal Telegram account.

### Authenticate

```bash
make tg-auth
# Phone number (with country code): +5511...
# Telegram verification code: 12345
```

The session is saved to `tokens/telegram.session` — no re-auth needed next time.

### Check status

```bash
make tg-status
# ✓  Your Name (+5511...)
```

### Read and send

```bash
make tg-dialogs                          # list recent chats
make tg-dialogs LIMIT=10
make tg-messages CHAT=@username          # messages from a chat
make tg-messages CHAT=+5511...           # by phone number
make tg-send CHAT=@username TEXT="Oi!"   # send a message
```

## Usage — Telegram Bot

The bot lets **you send commands to Nina** via Telegram. It uses batch mode: each invocation fetches pending commands, processes them, and exits — no background process required.

### Setup (one time)

1. Talk to [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token to `TELEGRAM_BOT_TOKEN` in `.env`
2. Run `make tg-bot` once
3. Open Telegram and send `/start` to your new bot
4. Run `make tg-bot` again — the bot replies with your chat ID
5. Copy that number to `TELEGRAM_OWNER_ID` in `.env`

### Run

```bash
make tg-bot
# Processed 1 command(s).
```

### Available bot commands

| Command | Description |
|---|---|
| `/start` | Welcome message and your chat ID |
| `/help` | List all commands |
| `/unread` | Unread emails across all Gmail accounts |
| `/latest` | Recent email headers |
| `/events` | Upcoming Calendar events |
| `/dialogs` | Recent Telegram chats |

### Automate with cron (optional)

To have Nina check for commands every minute, add to crontab (`crontab -e`):

```
* * * * * cd /path/to/nina && make tg-bot >> /tmp/nina-bot.log 2>&1
```

## Usage — LLM

Nina uses [LiteLLM](https://github.com/BerriAI/litellm) as a unified interface to any LLM provider. Switching from Groq to OpenAI or Anthropic is a one-line `.env` change — no code changes needed.

### Configure

Add to `.env`:

```
LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=gsk_...
```

To use a different provider:

```
LLM_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=sk_...

# or Anthropic
LLM_MODEL=anthropic/claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-...

# or local Ollama (no key needed)
LLM_MODEL=ollama/llama3.2
```

### Verify connectivity

```bash
make llm-ping
#   ✓  groq/llama-3.3-70b-versatile  →  OK
```

## Usage — Scheduler

Nina's internal scheduler keeps the process running and triggers jobs on a defined schedule — no external cron required.

```bash
make scheduler
# 2026-03-27 07:00:00  INFO  scheduler started — 0 job(s) registered
# Nina scheduler running — press Ctrl+C to stop
```

Jobs are registered in `nina/scheduler/jobs/` and added in `nina.py`. The scheduler handles `SIGINT` and `SIGTERM` for graceful shutdown.

## Project Layout

```
nina.py                      # CLI entry point
demo_digest.py               # LLM digest demo with real/simulated data
nina/
    errors.py                # shared exceptions (AuthError, GmailError, …)
    google/
        auth.py              # Google OAuth flow, token caching, auto-discovery
        gmail/
            client.py        # GmailClient + GmailMultiClient
        calendar/
            client.py        # CalendarClient (list_upcoming, list_next_days)
    telegram/
        client.py            # TgClient — Telethon user client (read/send as you)
        bot.py               # Telegram Bot batch processor (receive commands)
    llm/
        client.py            # LLMClient — LiteLLM wrapper (Groq, OpenAI, Anthropic, Ollama)
        digest.py            # LLM-powered daily brief
    scheduler/
        runner.py            # APScheduler-based daemon runner
        jobs/                # scheduled job implementations (added incrementally)
make/                        # setup.sh, test.sh, lint.sh
credentials/                 # credentials.json from Google Cloud Console (git-ignored)
tokens/                      # OAuth tokens, Telegram session, bot offset (all git-ignored)
tests/                       # pytest test suite
```

## Development

```bash
make setup      # Create .venv and install dependencies (first time only)
make test       # Run all tests
make lint       # Lint with ruff
make fmt        # Format code with ruff
make typecheck  # Type-check with mypy
make scheduler  # Start Nina's internal scheduler (daemon)
```

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
