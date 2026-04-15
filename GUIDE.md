# Nina — Command Guide

Complete reference for all Nina commands, available in both the **console** and **Telegram bot**.

Commands can be typed in the console directly (e.g. `presence office`) or sent to the bot with a leading `/` (e.g. `/presence office`). In the console, `/command` syntax also works.

Free-text input (natural language) is interpreted by the LLM in both interfaces.

---

## presence

Show or set your current presence status.

```
presence
presence <status>
presence <status> <note>
```

| Status | Meaning |
|---|---|
| `home` | Working from home |
| `office` | At the office |
| `out` | Out / on the move |
| `dnd` | Do not disturb — deep focus |

**Examples:**
```
presence
# office — at the office  (since 09:30)

presence home
# ✓ home — working from home

presence dnd "finishing the report"
```

**Effect on notifications:** When `dnd` is active, notifications are queued and delivered when you leave `dnd`.

---

## schedule

Create a calendar event directly, without LLM. Instant and reliable.

```
schedule <when> <title> [duration]
```

**Date/time formats:**

| Format | Example | Meaning |
|---|---|---|
| `HH:MM` | `16:00` | Today at 16:00 |
| `today HH:MM` | `today 16:00` | Today at 16:00 |
| `tomorrow HH:MM` | `tomorrow 09:00` | Tomorrow at 09:00 |
| `DD/MM HH:MM` | `29/03 14:00` | 29 March at 14:00 |
| `DD/MM/YYYY HH:MM` | `15/04/2024 10:00` | 15 April 2024 at 10:00 |

**Duration formats:** `1h` · `30min` · `1h30` · `1h30min` · `90min` (default: 60min)

**Examples:**
```
schedule 16:00 Meeting with Sandra 1h
schedule today 16:00 Consultation 30min
schedule tomorrow 09:00 Medical appointment
schedule 29/03 14:00 Training 2h
schedule 15/04/2024 10:00 Annual meeting 1h30
```

Start times are rounded down to the nearest 15-minute block. End times are rounded up. The event is created on the calendar account associated with your current presence (`profile`).

---

## memo / memos

Save a note or reminder; list, close, or dismiss existing memos.

```
memo <text>
memo <text> due <YYYY-MM-DD>
memos
memo done <id>
memo dismiss <id>
```

| Sub-command | Description |
|---|---|
| `memo <text>` | Save a new memo |
| `memo <text> due <date>` | Save with a due date |
| `memos` | List all open memos |
| `memo done <id>` | Mark memo as done |
| `memo dismiss <id>` | Dismiss memo without completing it |

The `<id>` is the first 8 characters shown in `memos` output (e.g. `a3f9c1b2`).

**Examples:**
```
memo call the supplier about the invoice
# ✓ Memo saved.

memo dentist appointment due 2026-04-15
# ✓ Memo saved.

memos
# [a3f9c1b2] call the supplier about the invoice
# [d7e20f41] dentist appointment  Due: 2026-04-15

memo done a3f9c1b2
# ✓ Memo marked as done.

memo dismiss d7e20f41
# ✓ Memo dismissed.
```

You can also create and manage memos using free text — see [Free-text (LLM)](#free-text-llm).

---

## workdays

Show your configured work schedule.

```
workdays
```

**Example output:**
```
  Timezone: America/Cuiaba

  Monday      09:00 → 18:00
  Tuesday     09:00 → 18:00
  Wednesday   09:00 → 18:00
  Thursday    09:00 → 18:00
  Friday      09:00 → 18:00
  Saturday    —
  Sunday      —
```

To change the schedule, use free text: `"work schedule Monday to Friday 8am to 5pm"`.

---

## timezone

Show or set the timezone used for work schedule and calendar events.

```
timezone
timezone <tz>
```

**Examples:**
```
timezone
# Timezone: America/Cuiaba

timezone America/Sao_Paulo
# ✓ Timezone set to: America/Sao_Paulo
```

Uses IANA timezone names. Full list at [iana.org/time-zones](https://www.iana.org/time-zones).

---

## context

Show your current work context — combines presence status and work schedule.

```
context
```

**Example output:**
```
  office
  ✓ work hours  ·  presence: office
```

Possible context labels: `at the office` · `home office` · `on the move` · `deep focus` · `overtime` · `working on weekend` · `off hours`.

---

## profile

Show or configure which Google accounts are active for each presence status.

```
profile
profile <status>
```

**Examples:**
```
profile
# Account profile:
#
# home — working from home
#   gmail:    personal@gmail.com
#   calendar: personal@gmail.com
#
# office — at the office
#   gmail:    work@company.com
#   calendar: work@company.com

profile office
```

To set account mappings, use free text:
```
at the office use work@company.com for calendar
at home use personal@gmail.com
```

---

## notify

Show or configure calendar notifications.

```
notify
notify reminder <minutes>
notify days <n>
```

| Sub-command | Description |
|---|---|
| `notify` | Show current settings |
| `notify reminder 10` | Set reminder to 10 minutes before event |
| `notify days 14` | Watch for new events up to 14 days ahead |

**Examples:**
```
notify
# Reminder: 15 min before  |  Watch: 7 days ahead

notify reminder 10
# ✓ Reminder set to 10 minutes before.

notify days 30
# ✓ Watch window set to 30 days.
```

**What Nina notifies you about:**
- 🔔 **Reminder** — X minutes before an event starts (all accounts)
- 📅 **New event** — someone scheduled something on your calendar
- ✏️ **Updated event** — an event was moved or renamed
- ❌ **Cancelled event** — an event was removed

Notifications are suppressed during `dnd` and outside work hours. When you return to work or leave `dnd`, queued notifications are delivered as a batch.

---

## lang

Show or set the interface language.

```
lang
lang <code>
```

Supported codes: `en` · `pt`

**Examples:**
```
lang
# Current language: en

lang pt
# ✓ Language changed to: pt
```

Changing the language updates both the console messages and the Telegram bot command descriptions.

---

## health

Show daemon status and uptime.

```
health
```

**Example output:**
```
  status   ok
  uptime   02:14:35
```

---

## Free-text (LLM)

In both the console and the Telegram bot, you can type anything in natural language. Nina uses a two-layer approach: first it checks for keyword signals in the text, then calls the LLM only for the matched domain (or a single router LLM call if no keywords matched).

**Domains handled:**

| Domain | Triggers | Result |
|---|---|---|
| Memo | "remind me", "save a note", "memo" | Creates memo or reminder with due date |
| Calendar blocking | time signals + scheduling words | Creates calendar event |
| Presence | presence status words | Updates presence |
| Work schedule | schedule / timezone words | Updates workdays or timezone |
| Profile | account mapping words | Associates account with presence |
| Notifications | "reminder", "notify", "alert" words | Updates notification settings |

**Calendar blocking examples:**
```
I'm in a meeting with Sandra for 1 hour
→ ✓ Meeting with Sandra  Sat, 29/03 · 10:00 → 11:00

schedule on Monday at 14:00 that I need to format a machine for Rafael
→ ✓ Format machine — Rafael  Mon, 30/03 · 14:00 → 15:00

add to my work calendar: Tuesday at 09:00 team standup 30min
→ ✓ Team standup  Tue, 31/03 · 09:00 → 09:30
   Account: work@company.com
```

A single message can contain multiple calendar events:
```
I'm in a meeting now for 30 min and at 16:00 I have a consultation for 1 hour
→ ✓ Meeting  Sat, 29/03 · 10:15 → 10:45
→ ✓ Consultation  Sat, 29/03 · 16:00 → 17:00
```

**Reminder examples** — "remind me" phrases create a memo with a due date instead of a calendar event:
```
remind me on Monday at 10h to format a machine for Rafael
→ ✓ Reminder for 2026-03-30 10:00 — format machine for Rafael

don't forget to send the report by Friday
→ ✓ Reminder for 2026-04-03 — send the report
```

**Memo examples:**
```
save a note: call the supplier about the invoice
→ ✓ Memo saved.

what memos do I have?
→ [a3f9c1b2] call the supplier about the invoice
```

**Presence examples:**
```
I just arrived at the office
→ ✓ office — at the office

heading home
→ ✓ home — working from home
```

**Work schedule and profile examples:**
```
work schedule Monday to Friday 9am to 6pm
→ ✓ Schedule updated.

at the office use work@company.com for calendar
→ ✓ Profile updated.
```

**Calendar account selection:** When the text mentions "work calendar" or "office", the work account is used regardless of current presence. When it mentions "personal calendar" or "home", the personal account is used.

---

## Console-only commands

### exit / quit

Exit the interactive console.

```
exit
quit
```

### help

Show available commands.

```
help
help <command>
```

---

## Telegram-only commands

### /start

Display a welcome message and your Telegram chat ID (needed for `TELEGRAM_OWNER_ID` in `.env`).

### /help

Show all available bot commands.

---

## HTTP /command (MacroDroid / External)

External integrations that don't support natural language can use the `/command` endpoint.

```
POST http://<NINA_IP>:8765/command
Content-Type: application/json
X-Api-Key: <your_key>

{"command": "/presence work"}
```

**Supported commands:**

| Command | Description | Example Body |
|---|---|---|
| `/presence {status}` | Set presence | `{"command":"/presence work"}` |
| `/presence {status} note:...` | Set presence with note | `{"command":"/presence dnd note:meeting"}` |
| `/status` | Get current status | `{"command":"/status"}` |
| `/health` | Health check | `{"command":"/health"}` |
| `/memo {text}` | Create a memo | `{"command":"/memo call supplier"}` |
| `/activity {text}` | Log activity to Calendar | `{"command":"/activity meeting with client"}` |

**Response format:**
```json
{"ok": true, "message": "✓ work — at the office"}
```

**MacroDroid setup** — Geofence → HTTP POST:
1. **Trigger:** Zone → Entry: "Office"
2. **Action:** HTTP Request → `POST http://192.168.1.x:8765/command`
   - Body: `{"command":"/presence work"}`
   - Header: `X-Api-Key: your_key`

---

## Activity Log

Log past work activities to Google Calendar (source of truth — data survives even if Nina goes down).

```
/activity meeting with client from 14h to 15h30
/activity deployed feature X
/activity code review PR #42 2h
```

Activities are rounded to 15-minute blocks (start rounds down, end rounds up). If no time is given, the system infers from context ("morning" = 9h, "afternoon" = 14h) or defaults to 11:00.

**End-of-day capture:** When you leave work (presence changes from `work` → `home`/`out`), the Telegram bot prompts you to log the day's activities. You can reply with multiple activities separated by commas:

```
"meeting with client 9h-10h, deployed feature X 10h-12h, code review afternoon"
```

This creates three separate events in Google Calendar.
