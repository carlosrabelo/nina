# Nina — skills (behaviour domains)

This document describes the **behaviour packages** under [`nina/skills/`](nina/skills/): what each domain does, how it is triggered, and where the code lives. It complements the [command reference](GUIDE.md) (CLI, HTTP, integrations).

For the same content in Portuguese, see [SKILL-PT.md](SKILL-PT.md).

---

## How skills connect to the product

- **Telegram bot** and **`nina console`** (with the daemon running) interpret free text through a shared pipeline: local pattern gates → optional **LLM router** → domain execution.
- **CLI exploratory commands** (`nina gmail …`, `nina calendar …`, etc.) live under [`nina/cli/`](nina/cli/) and are *not* the same as these skills; they are developer utilities.

---

## Intent routing (short)

See [`nina/core/intent/router.py`](nina/core/intent/router.py) for the full list of domains.

Rough pipeline:

1. **Layer 1** — per-skill `try_action` helpers (e.g. memo) where defined.
2. **Layer 2** — [`local_router.py`](nina/core/intent/local_router.py): regex and light NLP, no LLM.
3. **Layer 3** — LLM returns a `RouterIntent` (domain + fields).
4. **Layer 4** — extra LLM pass only for **blocking** and **workdays** when needed.

Domains resolved early (when patterns match) include **presence**, **memo**, **calendar** (read), **notifications**, and parts of **profile**. **Blocking** and **workdays** often need the dedicated interpreter.

---

## Skill catalogue

Alphabetical by domain id (see [AGENTS.md](AGENTS.md)).

### `activity_log` — structured activity on the calendar

- **Purpose:** Log or query past activities backed by Google Calendar (distinct from generic “list my events”).
- **Triggers:** Router domain `activity_log`; local signals in [`activity_log/patterns.py`](nina/skills/activity_log/patterns.py).
- **Code:** [`nina/skills/activity_log/`](nina/skills/activity_log/) (`interpreter`, `google_reader`, `google_writer`, `models`).
- **Storage:** Reads/writes **Google Calendar**; uses profile calendar accounts like other calendar flows.

---

### `blocking` — put time on the calendar

- **Purpose:** Create a blocking / focus event on Google Calendar when the user gives an explicit time or duration (“block 2pm”, “meeting for 1 hour”).
- **Triggers:** Router domain `blocking`; second LLM call via [`blocking.py`](nina/skills/calendar/blocking.py); HTTP [`POST /schedule`](nina/core/daemon/http.py) on the daemon.
- **Code:** [`nina/skills/calendar/blocking.py`](nina/skills/calendar/blocking.py), [`schedule_parser.py`](nina/skills/calendar/schedule_parser.py) where relevant.
- **Storage:** Writes through **Google Calendar API** (same client stack as read).

---

### `calendar` (read) — agenda questions

- **Purpose:** Read-only: list events in a window, search by keyword, suggest **free-busy** gaps (no event creation here).
- **Triggers:** Natural language (e.g. “what do I have tomorrow”, “events with dentist”, “free this afternoon”); router domain `calendar`; local patterns in [`local_router.try_calendar`](nina/core/intent/local_router.py).
- **Code:** [`nina/skills/calendar/execute.py`](nina/skills/calendar/execute.py), [`interpreter.py`](nina/skills/calendar/interpreter.py), plus Google client [`nina/integrations/google/calendar/client.py`](nina/integrations/google/calendar/client.py).
- **Account choice:** Uses [`Profile.best_calendar_accounts`](nina/skills/profile/models.py) from the current message and presence.
- **Storage:** Reads **Google Calendar**; Nina’s DB is not the source of truth for live events.

---

### `email_learning` — Gmail labels per sender

- **Purpose:** Persist per-account rules that map a sender (domain or address) to a Gmail **user** label; ingest recent inbox metadata, apply rules, and optionally surface Telegram prompts for new high-volume senders. Infer rules from messages that already carry a single user label.
- **Triggers:** **Not** an LLM router domain. Runs from the **scheduler** (`email_learning` job when the Telegram bot is configured), **`nina email sync`** / **`nina email infer-rules`**, **`/emailtag`** on Telegram, and **`emailtag`** / **`/emailtag`** in `nina console`.
- **Code:** [`nina/skills/email_learning/`](nina/skills/email_learning/) (`service.py`, [`infer_rules.py`](nina/skills/email_learning/infer_rules.py)); Gmail integration in [`nina/integrations/google/gmail/client.py`](nina/integrations/google/gmail/client.py).
- **Storage:** PostgreSQL tables via [`nina/core/store/repos/email_learning.py`](nina/core/store/repos/email_learning.py) — `email_messages`, `email_sender_rules`, `email_pending_labels` (see schema in [`nina/core/store/db.py`](nina/core/store/db.py)).

---

### `memo` — notes and reminders

- **Purpose:** Create, list, close, or dismiss memos; reminders with a resolved date/time.
- **Triggers:** Phrases like “memo …”, “remind me …”; Layer 1 memo interpreter; router domain `memo`.
- **Code:** [`nina/skills/memo/`](nina/skills/memo/) (`interpreter`).
- **Storage:** PostgreSQL tables via [`nina/core/store/repos/memo.py`](nina/core/store/repos/memo.py).

---

### `notifications` — how far ahead to warn you

- **Purpose:** Configure reminder minutes before events and how many days ahead to watch the calendar for changes.
- **Triggers:** Natural language (“notify me 30 minutes before”, “watch 2 days ahead”); HTTP routes on the daemon where exposed.
- **Code:** [`nina/skills/notifications/`](nina/skills/notifications/) (`store`, `interpreter`, `models`).
- **Storage:** PostgreSQL `kv_state`.

---

### `presence` — where you are now

- **Purpose:** Track `home` / `work` / `out` / `dnd` plus an optional short `note` (e.g. campus vs office).
- **Triggers:** Natural language in Telegram/console; HTTP `PUT /presence`, `POST /presence/{status}`; MacroDroid-style integrations.
- **Code:** [`nina/skills/presence/`](nina/skills/presence/) (`models`, `store`, `interpreter`).
- **Storage:** PostgreSQL `kv_state` (via `open_db` / KV helpers), not JSON files in production.

---

### `profile` — which Google accounts match each presence

- **Purpose:** Map Gmail and Calendar account emails per presence status so Nina picks the right account for Gmail/calendar actions.
- **Triggers:** Natural language (“at the office use work@company.com”); router domain `profile`.
- **Code:** [`nina/skills/profile/`](nina/skills/profile/) (`store`, `interpreter`, `models`).
- **Storage:** PostgreSQL `kv_state`.

---

### `workdays` — your weekly schedule and timezone

- **Purpose:** Define working hours, lunch, days off, and timezone for context (not the same as “I arrived at work” presence).
- **Triggers:** Router domain `workdays`; phrases about “Monday to Friday 9–5”, timezone changes; dedicated LLM interpreter when needed.
- **Code:** [`nina/skills/workdays/`](nina/skills/workdays/) (`store`, `interpreter`, `checker`, `models`).
- **Storage:** PostgreSQL `kv_state`.

---

## Related packages (not under `nina/skills/`)

- **Core store:** [`nina/core/store/`](nina/core/store/) — PostgreSQL connection, migrations, repositories for memos, actions, emails, and scheduled `calendar_events` used by the daemon/scheduler.
- **Daemon HTTP:** [`nina/core/daemon/http.py`](nina/core/daemon/http.py) — REST surface that may touch presence, workdays, schedule (`blocking`), notifications, etc.

When you change behaviour, keep this file aligned with [SKILL-PT.md](SKILL-PT.md), [GUIDE.md](GUIDE.md), and [README.md](README.md) — see [AGENTS.md](AGENTS.md).
