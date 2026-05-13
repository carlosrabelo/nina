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
        "/context — current context\n"
        "/gmail_label — pending sender → label suggestions\n"
        "/health — daemon status\n"
        "/lang — current language\n"
        "/lang <code> — change language (en|pt)\n"
        "/memo — notes and reminders\n"
        "/presence — current presence\n"
        "/presence <status> — change presence (home|work|out|dnd)\n"
        "/profile — account mapping per presence\n"
        "/schedule — schedule a calendar event\n"
        "/workdays — work schedule\n"
        "/timezone — current timezone\n\n"
        "/help <command> — show sub-options for a command"
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

    # ── gmail label learning (per Gmail account) ─────────────────────────────
    "gmail_label.suggest_telegram": (
        "Nina -- new sender pattern\n"
        "Account: {account}\n"
        "From: {sender}\n"
        "Sample subject: {subject}\n"
        "Seen (~30d): {count}\n\n"
        "Teach a label (this account only):\n"
        "/gmail_label {full_id} Your/Label-Name\n"
        "Ignore this sender forever:\n"
        "/gmail_label dismiss {full_id}\n"
        "(short id: {short_id}...)"
    ),
    "gmail_label.usage": (
        "/gmail_label — list open suggestions\n"
        "/gmail_label <id> <label> — save label for sender on that account\n"
        "/gmail_label rule add <account> <sender> <label> — add rule manually\n"
        "/gmail_label rules check — validate all rules\n"
        "/gmail_label dismiss <id> — ignore a suggestion (adds sender to ignore list)\n"
        "/gmail_label dismiss-all — ignore all open suggestions\n"
        "/gmail_label ignore list — list ignored senders\n"
        "/gmail_label ignore add <account> <sender> — add to ignored list\n"
        "/gmail_label ignore remove <account> <sender> — remove from ignored list\n"
        "Label must start with @ or ! (e.g. @Finance, !Important).\n"
        "Use at least 8 characters of the suggestion id."
    ),
    "gmail_label.no_pending": "No open sender suggestions.",
    "gmail_label.pending_header": "Open suggestions (account-specific rules):",
    "gmail_label.pending_line": "· [{account}] {sender}\n  id: {full_id}\n  hits: {hits}  sample: {subject}",
    "gmail_label.pending_not_found": "No matching open suggestion (check the id).",
    "gmail_label.ambiguous_id": "That id prefix matches more than one row — paste more characters.",
    "gmail_label.id_too_short": "Use at least 8 characters of the suggestion id.",
    "gmail_label.label_empty": "Label name cannot be empty.",
    "gmail_label.dismiss_ok": (
        "Ignored suggestion for {sender}.\n"
        "Future emails from this sender won't generate suggestions."
    ),
    "gmail_label.dismiss_all_ok": (
        "{count} suggestion(s) dismissed."
    ),
    "gmail_label.label_must_at": (
        "Label must start with @ or ! (e.g. @Finance, !Important)."
    ),
    "gmail_label.rule_added": (
        "Rule added: {sender} → [{label}] on {account}."
    ),
    "gmail_label.rule_updated": (
        "Rule updated: {sender} → [{label}] on {account} (was [{old_label}])."
    ),
    "gmail_label.check_ok": (
        "All {count} rule(s) look good."
    ),
    "gmail_label.check_no_rules": (
        "No rules in the database."
    ),
    "gmail_label.check_header": (
        "{count} issue(s) found across {rules} rule(s):"
    ),
    "gmail_label.check_bad_prefix": (
        "[{account}] {sender} → [{label}] — label must start with @ or !"
    ),
    "gmail_label.check_ignored": (
        "[{account}] {sender} → [{label}] — sender is also in the ignored list"
    ),
    "gmail_label.check_no_token": (
        "[{account}] {sender} → [{label}] — no OAuth token for this account"
    ),
    "gmail_label.check_missing_label": (
        "[{account}] {sender} → [{label}] — label does not exist in Gmail"
    ),
    "gmail_label.ignore_added": (
        "Ignored sender added: [{account}] {sender}."
    ),
    "gmail_label.ignore_removed": (
        "Removed from ignored list: [{account}] {sender}."
    ),
    "gmail_label.ignore_not_found": (
        "Sender not found in ignored list."
    ),
    "gmail_label.ignore_header": "Ignored senders (won't generate suggestions):",
    "gmail_label.ignore_empty": "No ignored senders.",
    "gmail_label.ignore_usage": (
        "/gmail_label ignore list — list ignored senders\n"
        "/gmail_label ignore add <account> <sender> — add to ignored list\n"
        "/gmail_label ignore remove <account> <sender> — remove from ignored list"
    ),
    "gmail_label.taught_ok": (
        "✓ Saved rule for {sender} → [{label}] on {account}.\n"
        "Applied to {applied} message(s) Nina had recorded."
    ),

    # ── calendar ──────────────────────────────────────────────────────────────
    "events.no_accounts": "No authenticated accounts.",
    "events.none":        "(no upcoming events)",
    "events.error":       "Error in {account}: {error}",
    "events.not_found":   "No events found.",
    "events.location":    "Location: {location}",

    # ── calendar blocking ─────────────────────────────────────────────────────
    "calendar.no_events":  "No upcoming events found.",
    "calendar.free_busy_header": "Free slots (≥30 min):",
    "calendar.free_slot": "{start} → {end}",
    "calendar.no_free_slot": "No continuous free slot of at least 30 minutes in this window.",
    "blocking.created":    "✓ {title}\n{date} · {start} → {end}\nAccount: {account}",
    "blocking.conflict":   "⚠️ Conflict: {titles}",
    "blocking.no_account": "No calendar account configured for current presence. Set it with /profile.",

    # ── profile ───────────────────────────────────────────────────────────────
    "profile.title":            "Account profile:",
    "profile.no_accounts":      "(not configured)",
    "profile.gmail":            "gmail:    {accounts}",
    "profile.calendar":         "calendar: {accounts}",
    "profile.set_ok":           "Profile updated.",
    "profile.empty":            "No accounts configured yet.\nSend a message like: \"at the office use work@company.com\"",
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
    "cmd.timezone":           "Show or set timezone",

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
    "cmd.memo":         "Save or list memos",
    "cmd.memos":        "List open memos",
    "cmd.gmail_label":   "Teach Gmail labels per account",

    # ── dialogs ───────────────────────────────────────────────────────────────
    "dialogs.none":   "No chats found.",
    "dialogs.error":  "Error: {error}",
    "dialogs.unread": " ({count} unread)",

    # ── /help <command> — per-command help (alphabetical) ──────────────────────
    "help.context": (
        "/context — current work context"
    ),
    "help.gmail_label": (
        "/gmail_label — list open suggestions\n"
        "/gmail_label <id> <label> — save label for sender on that account\n"
        "/gmail_label rule add <account> <sender> <label> — add rule manually\n"
        "/gmail_label rules check — validate all rules (prefix, Gmail, tokens, conflicts)\n"
        "/gmail_label dismiss <id> — ignore a suggestion (adds sender to ignore list)\n"
        "/gmail_label dismiss-all — ignore all open suggestions\n"
        "/gmail_label ignore list — list ignored senders\n"
        "/gmail_label ignore add <account> <sender> — add to ignored list\n"
        "/gmail_label ignore remove <account> <sender> — remove from ignored list\n\n"
        "Labels must start with @ or ! (e.g. @Finance, !Important).\n"
        "Use at least 8 characters of the suggestion id."
    ),
    "help.health": (
        "/health — daemon status and uptime"
    ),
    "help.lang": (
        "/lang — current language\n"
        "/lang <code> — change language (en|pt)"
    ),
    "help.memo": (
        "/memo <text> — save a new memo\n"
        "/memo <text> due <date> — save with due date\n"
        "/memos — list open memos\n"
        "/memo done <id> — mark as done\n"
        "/memo dismiss <id> — dismiss memo"
    ),
    "help.notify": (
        "/notify — show notification settings\n"
        "/notify reminder <min> — set reminder advance (minutes)\n"
        "/notify days <n> — set watch window (days)"
    ),
    "help.presence": (
        "/presence — current presence\n"
        "/presence <status> — set presence (home|work|out|dnd)\n"
        "/presence <status> <note> — set with a note"
    ),
    "help.profile": (
        "/profile — show account mapping per presence\n"
        "/profile <presence> — show for a specific presence"
    ),
    "help.schedule": (
        "/schedule HH:MM <title> [duration]\n"
        "/schedule today|tomorrow HH:MM <title> [duration]\n"
        "/schedule DD/MM HH:MM <title> [duration]\n"
        "/schedule DD/MM/YYYY HH:MM <title> [duration]\n\n"
        "Duration: 1h  30min  1h30  (default: 60min)"
    ),
    "help.timezone": (
        "/timezone — current timezone\n"
        "/timezone <tz> — set timezone (e.g. America/Cuiaba)"
    ),
    "help.workdays": (
        "/workdays — work schedule"
    ),
}
