# nina — Command and Integration Guide

Companion to [README.md](README.md). Covers the CLI surface, the HTTP API, slash commands, and integrations such as automatic presence updates from MacroDroid. When you change user-visible behaviour, keep this file and [README.md](README.md) aligned with [GUIDE-PT.md](GUIDE-PT.md) / [README-PT.md](README-PT.md) — see [AGENTS.md](AGENTS.md).

## Table of Contents

- [CLI commands](#cli-commands)
- [HTTP API](#http-api)
- [Presence states](#presence-states)
- [MacroDroid: automatic presence by location](#macrodroid-automatic-presence-by-location)
- [Slash commands](#slash-commands)

## CLI commands

Run from the project root with the venv:

```bash
.venv/bin/python -m nina <command>
# or after activating the venv: nina <command>
```

If you prefer make targets (loads `.env` automatically):

```bash
make console           # open interactive console (daemon must be running)
make run <command>     # run any nina CLI command
make run migrate to-postgres
```

Each command has a flat alias (good muscle memory for ex-`make` users) and a hierarchical form. Both are kept in the parser.

### Authentication

```bash
nina auth-google                         # alias: nina auth google
nina auth-telegram [--phone +5511...]    # alias: nina auth telegram
nina status-google                       # alias: nina status google
nina status-telegram                     # alias: nina status telegram
nina revoke ACCOUNT                      # remove a stored Google token
```

### Daemon and console

```bash
nina daemon          # production daemon: scheduler + HTTP API + Telegram bot
nina daemon --dev    # daemon without Telegram (for development)
nina console         # interactive REPL — talks to a running daemon over HTTP
```

`make dev-start` is a shortcut that opens both `daemon --dev` and `console` in a tmux session.

Docker Compose runs the **nina** app and **PostgreSQL** (`docker-compose.yml`). Copy `.env.example` → `.env` and set `DATABASE_URL` (host `postgres` inside the stack), `DATABASE_URL_HOST` (for tools on your machine when the DB port is published), plus path variables as documented in the README.

- **`make docker-start`** — sets `NINA_IMAGE` to `REGISTRY/IMAGE:<git short sha>` and runs `docker compose up -d --build` (recommended for a reproducible local image).
- **`make docker-stop`** — `docker compose down`.
- **`make docker-restart`** — `docker-stop` then `docker-start`.
- **`make docker-migrate`** — runs `scripts/migrate_to_postgres.py` in a one-off container (repo `./scripts` is bind-mounted).

Plain `docker compose up -d` uses whatever `NINA_IMAGE` is in `.env` (see `.env.example`). Add `docker-compose.override.yml` for a local `build: .` when you want to compile the image from this checkout.

### Gmail

```bash
nina gmail-latest [--account voce@gmail.com] [--limit 10]
nina gmail-unread [--account voce@gmail.com] [--limit 20]
nina gmail-search "from:boss is:unread" [--account voce@gmail.com] [--limit 20]
```

### Calendar

```bash
nina cal-list   [--account voce@gmail.com]
nina cal-events [--account voce@gmail.com] [--calendar primary] [--limit 10]
```

**Natural language (Telegram / console):** you can ask for your agenda in a time window, search events by keyword, or ask when you are free. That path is **read-only** and uses your profile’s calendar account for the current presence (or the account that best matches words like “work” vs “personal”).

**Creating time on the calendar** (blocking a slot, dentist at 9am, etc.) is handled by the **`blocking`** intent — same stack as `POST /schedule` on the daemon — not by the read-only calendar list. Phrases with an explicit time or duration (“às 15h”, “for 1 hour”) route there.

### Telegram

```bash
nina tg-bot                  # batch mode against the bot API
nina tg-setup                # discover TELEGRAM_OWNER_ID
nina tg-dialogs [--limit 20]
nina tg-messages CHAT [--limit 20]
nina tg-send CHAT TEXT
```

### LLM

```bash
nina llm-ping                # verify connectivity with the configured provider
```

### Code quality

```bash
nina typecheck               # run mypy on the nina package (alias of `make quality` step)
```

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

The daemon exposes `/command` for text commands, mirroring what the Telegram bot accepts. Useful for one-shot integrations and shell scripts.

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

The same commands work in the Telegram bot — just send them as a normal message.
