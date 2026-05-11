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

**`make run`** and **`make console`** invoke Python the same way as `python -m nina …`; Python loads the nearest `.env` (`load_project_dotenv` in `nina/cli/parser.py`). Outside Docker, non-empty **`DATABASE_URL_HOST`** and **`*_HOST`** path variables override the Compose-oriented names so one `.env` can serve both.

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
| `nina daemon [--dev]` | Long-lived process: internal scheduler (APScheduler), HTTP API, and Telegram bot. **`--dev`** turns off the Telegram bot only (HTTP + scheduler still run). Needs env vars such as `DATABASE_URL`, `NINA_HTTP_HOST`, `NINA_HTTP_PORT` (see README and `.env.example`). |
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

### Gmail label learning (CLI)

| Flat alias | Hierarchical | What it does |
|------------|--------------|--------------|
| `nina email-sync` | `nina email sync` | One-shot: scan inbox (recent window), upsert seen messages, apply existing per-account rules, optionally open Telegram suggestions for unknown high-volume senders (no Telegram when run from CLI alone). |
| `nina email-infer-rules` | `nina email infer-rules [--days D] [--max-per-account N] [--min-messages M]` | Scan all Gmail accounts over `newer_than:Dd`; when the same **user** label appears alone on enough messages from one sender, insert a matching rule (does not overwrite an existing rule). |

Teach or list pending labels from **Telegram** (`/emailtag`) or **`nina console`** (`emailtag` or `/emailtag` — hidden from the console `help` listing). Requires `gmail.modify` OAuth scope.

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

Docker Compose runs **nina** and **PostgreSQL** (`docker-compose.yml`). Copy `.env.example` → `.env` and set `DATABASE_URL` and paths as in the README.

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
nina email sync
nina cal-events --limit 3
nina llm-ping
```

`make dev-start` opens `daemon --dev` and `console` in one tmux session.

## HTTP API

When the daemon is running, an HTTP API answers on port `8765`. Defaults:

| Variable          | Typical value |
|-------------------|---------------|
| `NINA_HTTP_HOST`  | `0.0.0.0` (see `.env` / `.env.example`) |
| `NINA_HTTP_PORT`  | `8765`        |
| `NINA_API_KEY`    | empty (auth disabled) |

To accept connections from another device (your phone with MacroDroid, a script on another machine), put this in `.env`:

```
NINA_HTTP_HOST=0.0.0.0
NINA_HTTP_PORT=8765
NINA_API_KEY=choose-a-strong-key
```

Restart the daemon (`make dev-stop && make dev-start` or restart your `nina daemon` process). When `NINA_API_KEY` is set, every request must carry the header `X-API-Key: <key>`.
The console automatically sends `X-Api-Key` when `NINA_API_KEY` is set locally.

### Endpoints

| Method | Path                       | Purpose                                   |
|--------|----------------------------|-------------------------------------------|
| GET    | `/`                        | Service info, uptime, current presence    |
| GET    | `/health`                  | Liveness probe                            |
| GET    | `/status`                  | Flat presence + work-time context         |
| GET    | `/presence`                | Current presence state                    |
| PUT    | `/presence`                | Set presence (JSON body)                  |
| POST   | `/presence/{status}`       | Set presence (path-style; MacroDroid)     |
| POST   | `/command`                 | Slash-style command (see below)           |
| GET    | `/notifications/config`    | Reminder + watch-window config            |
| ...    | ...                        | See `/docs` (Swagger UI) for the full list|

Open `http://127.0.0.1:8765/docs` in a browser while the daemon is up to inspect every route interactively.

### Setting presence — examples

PUT with JSON body:

```bash
curl -X PUT http://127.0.0.1:8765/presence \
  -H "X-API-Key: $NINA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "work", "note": "office"}'
```

POST with path + query (no body — easier from MacroDroid):

```bash
curl -X POST "http://127.0.0.1:8765/presence/work?note=office" \
  -H "X-API-Key: $NINA_API_KEY"
```

Read it back:

```bash
curl -s -H "X-API-Key: $NINA_API_KEY" http://127.0.0.1:8765/presence
# {"status":"work","since":"...","note":"office"}
```

## Presence states

Four states are defined in `nina/skills/presence/models.py`:

| status  | meaning                                                       |
|---------|---------------------------------------------------------------|
| `home`  | at home — normal availability                                 |
| `work`  | at work in person (office, campus, client site)               |
| `out`   | out and about (commuting, errands) — short summaries          |
| `dnd`   | do not disturb — full silence                                 |

The `note` field is free-form text that travels with the state. Use it to carry sub-context (e.g. `office` vs `campus`) without changing the canonical status.

## MacroDroid: automatic presence by location

Goal: have your phone update presence automatically based on where you are. We define **three geofences** (home, campus, office) and use the `note` field to distinguish "in the office building" from "on campus but not in the office".

### State table

| location                                          | status | note     |
|---------------------------------------------------|--------|----------|
| inside the HOME geofence                          | `home` | —        |
| inside the OFFICE geofence (also inside CAMPUS)   | `work` | `office` |
| inside CAMPUS, outside OFFICE                     | `work` | `campus` |
| outside all three geofences                       | `out`  | —        |

OFFICE sits fully inside CAMPUS (the office building is on the campus). The `note` field carries the office/campus distinction; account routing keys off `status` and remains identical for both work zones.

### 1. Pre-requisites

- Daemon reachable from the phone:
  - `NINA_HTTP_HOST=0.0.0.0` and `NINA_API_KEY=...` in `.env`
  - Phone on the same Wi-Fi or VPN as the host
  - Find the host LAN IP (Linux): `ip -4 addr show | grep inet`
- MacroDroid installed on Android with location permission set to **"Allow all the time"** and battery optimisation **disabled** for the app
- A quick smoke test from the phone: open `http://<HOST_IP>:8765/health` in a browser (with the API key disabled temporarily, or use an HTTP client that supports headers); should return `{"status":"ok",...}`

### 2. Define the 3 geofences

In MacroDroid → **Settings → Geofences → +**:

1. **HOME** — center on your house, radius ~80–150 m
2. **CAMPUS** — center on the work site, radius wide enough to cover the entire campus (often 300–800 m)
3. **OFFICE** — center on your specific office building, radius 30–80 m (sits inside CAMPUS)

Use these exact names — the macros below reference them case-sensitively.

### 3. Reusable variables (recommended)

Create two MacroDroid global variables to avoid hard-coding values in every macro:

- `nina_host` (string) — e.g. `192.168.1.10:8765`
- `nina_api_key` (string) — your `NINA_API_KEY`

In every HTTP action below, the URL becomes `http://[nina_host]/presence/<status>?note=<note>` and the header becomes `X-API-Key: [nina_api_key]`.

### 4. Common HTTP action template

Every macro uses the same MacroDroid action: **Connectivity → HTTP Request**.

- **Method**: POST
- **URL**: `http://[nina_host]/presence/<status>?note=<note>`
- **Headers**: `X-API-Key: [nina_api_key]`
- **Body**: empty
- Pick **Yes** for "Wait for response" only if you want failure notifications

### 5. The six macros

Create one macro per geofence transition. Each has a single trigger, optional constraint, and the HTTP action above.

#### Nina presence — Home in

- **Trigger**: Geofence → Entered → HOME
- **Action**: POST `http://[nina_host]/presence/home`

#### Nina presence — Home out

- **Trigger**: Geofence → Exited → HOME
- **Constraint**: Not inside CAMPUS, Not inside OFFICE
- **Action**: POST `http://[nina_host]/presence/out`

#### Nina presence — Office in

- **Trigger**: Geofence → Entered → OFFICE
- **Action**: POST `http://[nina_host]/presence/work?note=office`

#### Nina presence — Office out

- **Trigger**: Geofence → Exited → OFFICE
- **Constraint**: Inside CAMPUS
- **Action**: POST `http://[nina_host]/presence/work?note=campus`

#### Nina presence — Campus in

- **Trigger**: Geofence → Entered → CAMPUS
- **Constraint**: Not inside OFFICE
- **Action**: POST `http://[nina_host]/presence/work?note=campus`

#### Nina presence — Campus out

- **Trigger**: Geofence → Exited → CAMPUS
- **Constraint**: Not inside HOME
- **Action**: POST `http://[nina_host]/presence/out`

The constraints handle the overlap: when you exit OFFICE, you're still inside CAMPUS so we keep `work` (note flips from `office` to `campus`). When you finally leave CAMPUS, we drop to `out` unless HOME has already taken over.

### 6. Verify

While the daemon is running:

```bash
watch -n 2 'curl -s -H "X-API-Key: $NINA_API_KEY" http://127.0.0.1:8765/presence'
```

Walk through the geofences and watch the status and note flip. Same check from your phone (open `/presence` in a browser-style HTTP client) is just as good.

### 7. Tips

- **Initial seed** — Android sometimes won't fire an "enter" event for a geofence you were already inside when it was created. Walk out and back in once to seed.
- **Battery optimisation** — Android can throttle geofence callbacks aggressively. Whitelist MacroDroid in **Settings → Apps → MacroDroid → Battery → Unrestricted**.
- **Manual override** — keep `nina presence work` from the console or `/presence dnd` from Telegram handy for the times the automation is wrong (e.g. working from a café).
- **DND from location** — `dnd` is intentionally not wired here; it works better as an explicit signal (Telegram command, a Focus Mode trigger, or a calendar-event-based macro).

## Slash commands

The daemon exposes `/command` for a **subset** of text commands the Telegram bot also understands. Useful for one-shot integrations and shell scripts.

```bash
curl -X POST http://127.0.0.1:8765/command \
  -H "X-API-Key: $NINA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command": "/presence work note:campus"}'
```

Supported commands:

| Command                   | Effect                                            |
|---------------------------|---------------------------------------------------|
| `/presence <status> [note:...]` | Set presence (same statuses as the enum)    |
| `/status`                 | Return current presence + workday context         |
| `/health`                 | Liveness check                                    |
| `/memo <text>`            | Create a memo                                     |
| `/activity <text>`        | Log past activity                                 |

Commands such as **`/emailtag`** are available in the **Telegram bot** and **`nina console`**; they are **not** handled by `POST /command` (subset above).

The table above works in the Telegram bot too — send them as a normal message.
