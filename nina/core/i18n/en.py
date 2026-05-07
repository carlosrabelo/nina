STRINGS: dict[str, str] = {
    # ── start / help ──────────────────────────────────────────────────────────
    "start.greeting": (
        "Hi! I'm Nina, your personal assistant.\n\n"
        "Use /help for available commands.\n\n"
        "Your chat ID: {chat_id}"
    ),
    "start.lang_detected": "Language detected: {lang}. Use /lang to change it.",
    "lang.current":  "Current language: {code}",
    "lang.set_ok":   "✓ Language changed to: {code}",
    "lang.invalid":  "Unknown language '{code}'. Supported: {supported}",
    "help.text": (
        "Available commands:\n\n"
        "🤖 Nina\n"
        "/presence — current presence\n"
        "/presence <status> — change presence (home|work|out|dnd)\n"
        "/health — daemon status\n"
        "/workdays — work schedule\n"
        "/timezone — current timezone\n"
        "/context — current context\n"
        "/lang — current language\n"
        "/lang <code> — change language (en|pt)\n"
        "/profile — account mapping per presence\n"
    ),

    # ── presence ──────────────────────────────────────────────────────────────
    "presence.label.home":   "at home",
    "presence.label.work": "at work",
    "presence.label.out":    "out / on the move",
    "presence.label.dnd":    "do not disturb",
    "presence.current":      "{status} — {label}\nSince: {since}{note}",
    "presence.since_prefix": "since",
    "presence.set_ok":       "✓ {status} — {label}",
    "presence.invalid":      "Invalid status. Use: {valid}",

    # ── health ────────────────────────────────────────────────────────────────
    "health.online": "✓ Nina online\nUptime: {uptime}",

    # ── workdays ──────────────────────────────────────────────────────────────
    "workdays.timezone":         "Timezone: {tz}",
    "workdays.timezone_set":     "✓ Timezone set to: {tz}",
    "workdays.timezone_invalid": "Unknown timezone '{tz}'. Use a valid tz name, e.g. America/Cuiaba.",
    "workdays.hours":    "{start} → {end}",
    "workdays.lunch":    "lunch: {start} → {end}",
    "workdays.off":      "—",
    "day.0": "Monday",
    "day.1": "Tuesday",
    "day.2": "Wednesday",
    "day.3": "Thursday",
    "day.4": "Friday",
    "day.5": "Saturday",
    "day.6": "Sunday",

    # ── context ───────────────────────────────────────────────────────────────
    "context.label.dnd":          "deep focus",
    "context.label.out":          "on the move",
    "context.label.lunch":        "lunch break",
    "context.label.weekend_work": "working on the weekend",
    "context.label.overtime":     "overtime",
    "context.label.home_office":  "home office",
    "context.label.office":       "at the office",
    "context.label.off_hours":    "off hours",
    "context.flag.overtime":      "overtime",
    "context.flag.weekend":       "weekend",
    "context.in_work_time":       "✓ work hours",
    "context.lunch_time":         "🍽️ lunch break",
    "context.off_hours":          "✗ outside work hours",
    "lunch.reminder":             "🍽️ Time for lunch! Don't forget to take a break.",

    # ── gmail ─────────────────────────────────────────────────────────────────
    "unread.none":    "No unread emails.",
    "unread.error":   "Error: {error}",
    "unread.item":    "[{account}]\nFrom: {sender}\nSubject: {subject}\nPreview: {snippet}",
    "latest.none":    "No emails found.",
    "latest.error":   "Error: {error}",
    "latest.from":    "From: {sender}",
    "latest.subject": "Subject: {subject}",

    # ── calendar ──────────────────────────────────────────────────────────────
    "events.no_accounts": "No authenticated accounts.",
    "events.none":        "(no upcoming events)",
    "events.error":       "Error in {account}: {error}",
    "events.not_found":   "No events found.",
    "events.location":    "Location: {location}",

    # ── calendar blocking ─────────────────────────────────────────────────────
    "calendar.no_events":  "No upcoming events found.",
    "blocking.created":    "✓ {title}\n{date} · {start} → {end}\nAccount: {account}",
    "blocking.conflict":   "⚠️ Conflict: {titles}",
    "blocking.no_account": "No calendar account configured for current presence. Set it with /profile.",

    # ── profile ───────────────────────────────────────────────────────────────
    "profile.title":            "Account profile:",
    "profile.no_accounts":      "(not configured)",
    "profile.gmail":            "gmail:    {accounts}",
    "profile.calendar":         "calendar: {accounts}",
    "profile.set_ok":           "✓ Profile updated.",
    "profile.empty":            "No accounts configured yet.\nSend a message like: \"at the office use work@company.com\"",
    "help.profile":             "  profile   Show account mapping per presence\n  profile <presence>   Show for specific presence",
    "cmd.profile":              "Show account profile per presence",

    # ── llm interpreter ───────────────────────────────────────────────────────
    "llm.presence_set":    "✓ {status} — {label}",
    "llm.schedule_set":    "✓ Schedule updated.",
    "llm.not_understood":  "I couldn't understand that.",
    "llm.unavailable":     "LLM not configured. Set LLM_MODEL and the API key in .env.",

    # ── console ───────────────────────────────────────────────────────────────
    "console.intro":          "Nina console  —  type 'help' for commands, 'exit' to quit.\nRequires the daemon to be running: nina daemon\n",
    "console.bye":            "Bye.",
    "console.unknown_cmd":    "  Unknown command: '{cmd}'. Type 'help' for available commands.",
    "console.health.status":  "  status   {value}",
    "console.health.uptime":  "  uptime   {value}",
    "console.context.presence": "  {work}  ·  presence: {presence}",
    "help.presence":          "  presence                    Show current presence status\n  presence <status>           Set presence  (home | work | out | dnd)\n  presence <status> <note>    Set with a note",
    "help.health":            "  health   Show daemon status and uptime",
    "help.workdays":          "  workdays   Show work schedule",
    "help.timezone":          "  timezone              Show current timezone\n  timezone <tz>         Set timezone  (e.g. America/Cuiaba)",
    "cmd.timezone":           "Show or set timezone",
    "help.context":           "  context   Show current work context (presence × schedule)",
    "help.lang":              "  lang              Show current language\n  lang <code>       Set language  (en | pt)",
    "help.exit":              "  exit / quit   Exit the console",

    # ── schedule command ──────────────────────────────────────────────────────
    "schedule.created":  "✓ {title}\n{date} · {start} → {end}\nAccount: {account}",
    "schedule.conflict": "⚠️ Conflict: {titles}",
    "schedule.no_account": "No calendar account configured for current presence. Set it with /profile.",
    "schedule.parse_error": (
        "Could not parse. Usage:\n"
        "  schedule HH:MM <title> [duration]\n"
        "  schedule today 16:00 Meeting 1h\n"
        "  schedule tomorrow 10:00 Appointment 30min\n"
        "  schedule 29/03 14:00 Training 2h"
    ),
    "help.schedule": (
        "  schedule HH:MM <title> [duration]\n"
        "  schedule today|tomorrow HH:MM <title> [duration]\n"
        "  schedule DD/MM HH:MM <title> [duration]\n"
        "  schedule DD/MM/YYYY HH:MM <title> [duration]\n"
        "\n"
        "  Duration: 1h  30min  1h30  (default: 60min)"
    ),
    "cmd.schedule":  "Schedule a calendar event directly",

    # ── bot command descriptions (shown in Telegram autocomplete) ─────────────
    "cmd.start":     "Start Nina",
    "cmd.help":      "List available commands",
    "cmd.lang":      "Show or change language",
    "cmd.presence":  "Show or set presence status",
    "cmd.health":    "Daemon status and uptime",
    "cmd.workdays":  "Show work schedule",
    "cmd.context":   "Current work context",
    "cmd.unread":    "Unread emails",
    "cmd.latest":    "Recent emails",
    "cmd.events":    "Upcoming calendar events",
    "cmd.dialogs":   "Recent Telegram chats",

    # ── notifications ─────────────────────────────────────────────────────────
    "notify.config":         "Reminder: {reminder_minutes} min before  |  Watch: {watch_days} days ahead",
    "notify.reminder_set":   "✓ Reminder set to {minutes} minutes before.",
    "notify.days_set":       "✓ Watch window set to {days} days.",
    "notify.invalid_value":  "Invalid value '{value}'. Must be a positive integer.",
    "notify.usage":          "  notify                    Show notification settings\n  notify reminder <min>     Set reminder advance (minutes)\n  notify days <n>           Set watch window (days)",
    "help.notify":           "  notify                    Show notification settings\n  notify reminder <min>     Set reminder advance (minutes)\n  notify days <n>           Set watch window (days)",
    "cmd.notify":            "Show or configure notifications",

    # ── memo ──────────────────────────────────────────────────────────────────
    "memo.saved":       "✓ Memo saved.",
    "memo.remind_set":  "✓ Reminder for {date} — {subject}",
    "memo.done":        "✓ Memo marked as done.",
    "memo.dismissed":   "✓ Memo dismissed.",
    "memo.not_found":   "Memo not found.",
    "memo.none_open":   "No open memos.",
    "memo.item":        "[{index}] {text}{due}",
    "memo.due":         "  Due: {date}",
    "memo.usage":       "  memo <text>          Save a new memo\n  memo <text> due <date>  Save with due date (YYYY-MM-DD)\n  memos                List open memos\n  memo done <id>       Mark memo as done\n  memo dismiss <id>    Dismiss memo",
    "help.memo":        "  memo <text>          Save a new memo\n  memo <text> due <date>  Save with due date\n  memos                List open memos\n  memo done <id>       Mark as done\n  memo dismiss <id>    Dismiss",
    "cmd.memo":         "Save or list memos",
    "cmd.memos":        "List open memos",

    # ── dialogs ───────────────────────────────────────────────────────────────
    "dialogs.none":   "No chats found.",
    "dialogs.error":  "Error: {error}",
    "dialogs.unread": " ({count} unread)",
}
