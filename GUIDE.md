# nina — Command and Integration Guide

Companion to [README.md](README.md). Covers the CLI surface, the HTTP API, slash commands, and integrations such as automatic presence updates from MacroDroid. When you change user-visible behaviour, keep this file and [README.md](README.md) aligned with [GUIDE-PT.md](GUIDE-PT.md) / [README-PT.md](README-PT.md) — see [AGENTS.md](AGENTS.md).

## Table of Contents

- [CLI commands](#cli-commands)
- [Full CLI command list](#full-cli-command-list)
- [HTTP API](#http-api)
- [Presence states](#presence-states)
- [MacroDroid: automatic presence by location](#macrodroid-automatic-presence-by-location)
- [Slash commands](#slash-commands)

## CLI commands

### How to run `nina`

From the project root with the venv:

```bash
.venv/bin/python -m nina <command> [args...]
# or, after `source .venv/bin/activate` and `pip install -e .`:
nina <command> [args...]
```

**`make run`** and **`make console`** invoke Python the same way as `python -m nina …`; Python loads the nearest `.env` (`load_project_dotenv` in `nina/cli/parser.py`). If `DATABASE_URL` is unset, it is built from `POSTGRES_*` (see README). Inside Docker, relative `DATA_DIR` / `TOKENS_DIR` / `SESSIONS_DIR` / `GOOGLE_CREDENTIALS_FILE` values get a leading `/` so the same paths work as on the host.

```bash
make run gmail latest --limit 5
make run migrate to-postgres    # Makefile dispatches to scripts/migrate_to_postgres.py (not a `nina` subcommand)
```

**`make console`** opens the interactive console (the daemon must be running). Prefer `make console` rather than `make run console`.

Where a feature offers both forms, this guide lists a **flat alias** (e.g. `nina gmail-latest`) and the **hierarchical** form (`nina gmail latest`); they are equivalent.

### Built-in help

```bash
.venv/bin/python -m nina --help
.venv/bin/python -m nina gmail --help
.venv/bin/python -m nina gmail latest -h
```

## Full CLI command list

### Lifecycle and shell

| Command | What it does |
|---------|----------------|
| `nina daemon [--dev]` | Long-lived process: internal scheduler (APScheduler), HTTP API, and Telegram bot. **`--dev`** turns off the Telegram bot only (HTTP + scheduler still run). Needs env such as Postgres credentials (or `DATABASE_URL`), `NINA_HTTP_HOST`, `NINA_HTTP_PORT` (see README and `.env.example`). |
| `nina console` | Interactive REPL that talks to an **already running** daemon over HTTP (uses `NINA_HTTP_*`; sends `X-Api-Key` when `NINA_API_KEY` is set). |

### Google authentication

| Flat alias | Hierarchical | What it does |
|------------|--------------|----------------|
| `nina auth-google` | `nina auth google` | Browser OAuth; stores one Google account under `TOKENS_DIR`. Run again for more accounts. |
| `nina auth-telegram [--phone +…]` | `nina auth telegram [--phone +…]` | Interactive login for the **Telegram user** API (not the bot); session under `SESSIONS_DIR`. |
| `nina status-google` | `nina status google` | Lists discovered Google accounts and whether each token looks valid. |
| `nina status-telegram` | `nina status telegram` | Shows if the Telegram **user** client is authorized. |
| — | `nina revoke <email>` | Removes the stored Google OAuth token for that account (no flat alias). |

### Gmail (exploratory)

| Flat alias | Hierarchical | What it does |
|------------|--------------|----------------|
| `nina gmail-latest [--account …] [--limit N]` | `nina gmail latest …` | Recent message headers per account (or one account). |
| `nina gmail-unread [--account …] [--limit N]` | `nina gmail unread …` | Unread messages (all accounts if `--account` omitted). |
| `nina gmail-search "QUERY" [--account …] [--limit N]` | `nina gmail search "QUERY" …` | Gmail search using [Gmail search operators](https://support.google.com/mail/answer/7190). |
| `nina gmail-labels [--account …] [--user-only]` | `nina gmail labels …` | **Gmail only:** lists labels that exist **in your Gmail account** right now (API `users.labels.list`): id, type (`system` / `user`), and name. This is **not** Nina’s learned sender→label rules in PostgreSQL. **`--user-only`** limits output to user-created labels. |

### Gmail label learning (CLI)

| Flat alias | Hierarchical | What it does |
|------------|--------------|--------------|
| `nina gmail-label-process [--verbose] [--days D] [--max-per-account N] [--account …]` | `nina gmail_label process [--verbose] [--days D] [--max-per-account N] [--account …]` | **Processing run:** fetch via **`NINA_EMAIL_SYNC_QUERY`**, upsert **`email_messages`**, apply **`email_sender_rules`** in Gmail. Messages that already have **`tagged_at`** in **`email_messages`** are skipped early (no header upsert, no rule work). **`--days`** sets or replaces the first `newer_than:Dd` in the query (wide backfill). **`--max-per-account`** caps Gmail list size per account (env default max 500; CLI allows up to **5000**). **`--account`** filters to one Gmail account. **`--verbose`** (`-v`) prints progress on stderr. |
| `nina gmail-label-rules` | `nina gmail_label rules list [--account …]` | **PostgreSQL:** lists **learned** sender rules Nina will apply (`email_sender_rules`: account, normalized sender, Gmail user label name, archive flag, `created_at`). No Gmail API calls. |
| | `nina gmail_label rules check` | **Validate rules:** check all rules for invalid prefix, missing Gmail label, no OAuth token, or sender also in ignored list. |
| `nina gmail-label-infer` | `nina gmail_label infer-rules [--days D] [--max-per-account N] [--min-messages M] [--verbose]` | **Rules only:** scan Gmail over `newer_than:Dd` and **insert** new **`email_sender_rules`** when one user label appears alone on enough messages from a sender (does not overwrite an existing rule). Does **not** write `email_messages` or change the inbox — run **`nina gmail_label process`** afterward to ingest and apply. **`--verbose`** (`-v`) prints progress on stderr. |
| | `nina gmail_label pending scan [--days D] [--min-messages M] [--account …] [-v]` | **Pending suggestions:** scan `email_messages` for senders without a rule, not ignored, with enough untagged messages. Creates pending suggestions shown via `/gmail_label`. |
| `nina gmail_label rule add <account> <sender> <@label>` | (same) | **Add rule manually:** create a sender rule directly without a pending suggestion. Label must start with **`@`** or **`!`**. If a rule already exists for that account+sender, the label is updated. |
| `nina gmail_label ignore list [--account …]` | (same) | List ignored senders that will never generate label suggestions. |
| `nina gmail_label ignore add <account> <sender>` | (same) | Add a sender to the ignore list. Also happens automatically when you **dismiss** a pending suggestion. |
| `nina gmail_label ignore remove <account> <sender>` | (same) | Remove a sender from the ignore list so suggestions can appear again. |

Teach or list pending labels from **Telegram** (`/gmail_label`) or **`nina console`** (`gmail_label`; see `help` / `help gmail_label` in the console). Use **`nina gmail_label pending scan`** to find new sender candidates in `email_messages`. Dismissing a suggestion automatically adds the sender to the **ignored list** (`email_ignored_senders`), preventing future suggestions. **`/gmail_label dismiss-all`** clears all open suggestions at once. Labels must start with **`@`** or **`!`** (e.g. `@Finance`, `!Important`). **`/gmail_label rules check`** validates all rules for common issues. Manage ignored senders with **`/gmail_label ignore list|add|remove`** or **`nina gmail_label ignore ...`**. Requires `gmail.modify` OAuth scope.

### Google Calendar (exploratory CLI)

| Flat alias | Hierarchical | What it does |
|------------|--------------|----------------|
| `nina cal-list [--account …]` | `nina calendar list …` | Lists calendar names and IDs. |
| `nina cal-events [--account …] [--calendar ID] [--limit N]` | `nina calendar events …` | Upcoming events; `--calendar` defaults to `primary`. |

**Natural language (Telegram / console):** agenda questions (windows, keyword search, free/busy) go through the bot or `nina console` with the daemon — **read-only**, using the calendar account from your profile / presence (or best match from words like “work” vs “personal”). **Creating** calendar time (blocks, “dentist at 9am”) uses the **`blocking`** intent / `POST /schedule`, not these exploratory commands.

### Telegram user client (exploratory)

| Flat alias | Hierarchical | What it does |
|------------|--------------|----------------|
| `nina tg-bot` | `nina tg bot` | Batch processing of bot-related commands from the environment (scripting / advanced). |
| `nina tg-setup` | `nina tg setup` | Helps discover `TELEGRAM_OWNER_ID` for the bot. |
| `nina tg-dialogs [--limit N]` | `nina tg dialogs …` | Lists recent dialogs for the **user** session. |
| `nina tg-messages CHAT [--limit N]` | `nina tg messages CHAT …` | Recent messages; `CHAT` = numeric id, `@username`, or phone. |
| `nina tg-send CHAT TEXT` | `nina tg send CHAT TEXT` | Sends a message as the **user** client. |

### LLM

| Flat alias | Hierarchical | What it does |
|------------|--------------|----------------|
| `nina llm-ping` | `nina llm ping` | Single call to `LLM_MODEL` to verify keys and connectivity. |

### Code quality

| Command | What it does |
|---------|----------------|
| `nina typecheck [paths…]` | Runs `mypy` (default: installed `nina` package). Same role as the mypy step in `make quality`. |

### Docker and Compose

Docker Compose runs **nina** and **PostgreSQL** (`docker-compose.yml`). Copy `.env.example` → `.env`, set `POSTGRES_*` (and paths as in the README); `DATABASE_URL` is optional.

- **`make docker-start`** — sets `NINA_IMAGE` to `REGISTRY/IMAGE:<git short sha>` and runs `docker compose up -d --build`.
- **`make docker-stop`** — `docker compose down`.
- **`make docker-restart`** — `docker-stop` then `docker-start`.
- **`make docker-migrate`** — runs `scripts/migrate_to_postgres.py` in a one-off container (`./scripts` bind-mounted).

Plain `docker compose up -d` uses `NINA_IMAGE` from `.env`. Use `docker-compose.override.yml` with `build: .` for a local image build.

### Quick examples

```bash
nina auth-google && nina status-google
nina daemon --dev          # terminal A
make console               # terminal B — host `.env` must point at DB + daemon
nina gmail-unread --limit 5
nina gmail labels --user-only
nina gmail_label process
# optional: wide window, more messages; already-tagged rows are skipped early
nina gmail_label process --days 365 --max-per-account 2000 -v
nina gmail_label rules
nina cal-events --limit 3
nina llm-ping
```

`make dev-start` opens `daemon --dev` and `console` in one tmux session.

## HTTP API

Moved to [API.md](API.md) (HTTP API, endpoints, MacroDroid examples).
