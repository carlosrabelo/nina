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
        "/presence <status> — change presence (home|office|out|dnd)\n"
        "/health — daemon status\n"
        "/workdays — work schedule\n"
        "/context — current context\n"
        "/lang — current language\n"
        "/lang <code> — change language (en|pt)\n\n"
        "📧 Gmail\n"
        "/unread — unread emails\n"
        "/latest — recent emails\n\n"
        "📅 Calendar\n"
        "/events — upcoming events\n\n"
        "💬 Telegram\n"
        "/dialogs — recent chats\n"
    ),

    # ── presence ──────────────────────────────────────────────────────────────
    "presence.label.home":   "at home",
    "presence.label.office": "at the office",
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
    "context.label.weekend_work": "working on the weekend",
    "context.label.overtime":     "overtime",
    "context.label.home_office":  "home office",
    "context.label.office":       "at the office",
    "context.label.off_hours":    "off hours",
    "context.flag.overtime":      "overtime",
    "context.flag.weekend":       "weekend",
    "context.in_work_time":       "✓ work hours",
    "context.off_hours":          "✗ outside work hours",

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

    # ── llm interpreter ───────────────────────────────────────────────────────
    "llm.presence_set":    "✓ {status} — {label}",
    "llm.schedule_set":    "✓ Schedule updated.",
    "llm.not_understood":  "I couldn't understand that. Try /presence or /workdays.",
    "llm.unavailable":     "LLM not configured. Set LLM_MODEL and the API key in .env.",

    # ── console ───────────────────────────────────────────────────────────────
    "console.intro":          "Nina console  —  type 'help' for commands, 'exit' to quit.\nRequires the daemon to be running: nina daemon\n",
    "console.bye":            "Bye.",
    "console.unknown_cmd":    "  Unknown command: '{cmd}'. Type 'help' for available commands.",
    "console.health.status":  "  status   {value}",
    "console.health.uptime":  "  uptime   {value}",
    "console.context.presence": "  {work}  ·  presence: {presence}",
    "help.presence":          "  presence                    Show current presence status\n  presence <status>           Set presence  (home | office | out | dnd)\n  presence <status> <note>    Set with a note",
    "help.health":            "  health   Show daemon status and uptime",
    "help.workdays":          "  workdays   Show work schedule",
    "help.timezone":          "  timezone              Show current timezone\n  timezone <tz>         Set timezone  (e.g. America/Cuiaba)",
    "cmd.timezone":           "Show or set timezone",
    "help.context":           "  context   Show current work context (presence × schedule)",
    "help.lang":              "  lang              Show current language\n  lang <code>       Set language  (en | pt)",
    "help.exit":              "  exit / quit   Exit the console",

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

    # ── dialogs ───────────────────────────────────────────────────────────────
    "dialogs.none":   "No chats found.",
    "dialogs.error":  "Error: {error}",
    "dialogs.unread": " ({count} unread)",
}
