# nina/telegram/bot.py
"""Telegram Bot — persistent and batch mode."""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from nina.errors import CalendarError, ConfigError, GmailError, TelegramError
from nina.google.auth import discover_accounts
from nina.google.calendar.client import CalendarClient
from nina.google.gmail.client import GmailMultiClient
from nina.i18n import t
from nina.locale.models import SUPPORTED, LocaleConfig
from nina.locale.store import load as load_locale, save as save_locale
from nina.telegram.client import TgClient

_MAX_MSG = 4000  # Telegram hard limit is 4096 chars; stay under to be safe


# ---------------------------------------------------------------------------
# Offset persistence
# ---------------------------------------------------------------------------

def _offset_file(sessions_dir: Path) -> Path:
    return sessions_dir / "bot_offset.txt"


def load_offset(sessions_dir: Path) -> int:
    """Return the stored update offset, or 0 if not yet set."""
    f = _offset_file(sessions_dir)
    return int(f.read_text().strip()) if f.exists() else 0


def save_offset(sessions_dir: Path, offset: int) -> None:
    """Persist the next offset so the next run skips already-processed updates."""
    sessions_dir.mkdir(parents=True, exist_ok=True)
    _offset_file(sessions_dir).write_text(str(offset))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.bot_data.get("lang", "pt")


_COMMAND_NAMES = [
    "start", "help", "lang", "presence", "health",
    "workdays", "timezone", "context", "profile", "schedule", "notify",
    "obsidian",
    "memo", "memos",
]


async def _set_commands(app: Application, lang: str) -> None:
    """Register localized command descriptions with Telegram."""
    commands = [BotCommand(name, t(f"cmd.{name}", lang)) for name in _COMMAND_NAMES]
    await app.bot.set_my_commands(commands)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def handle_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    data_dir: Path = ctx.bot_data["data_dir"]
    tg_lang_code = (update.effective_user.language_code or "") if update.effective_user else ""

    # Auto-detect language on first /start if not yet saved
    locale = load_locale(data_dir)
    if tg_lang_code:
        detected = tg_lang_code.split("-")[0].lower()
        if detected in SUPPORTED and detected != locale.lang:
            locale = LocaleConfig(lang=detected)
            save_locale(locale, data_dir)
            ctx.bot_data["lang"] = detected

    lang = _lang(ctx)
    await update.message.reply_text(
        t("start.greeting", lang, chat_id=update.message.chat_id)
    )


async def handle_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(t("help.text", _lang(ctx)))


async def handle_unread(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(ctx)
    try:
        nina = GmailMultiClient.from_env()
        messages = nina.list_unread(max_results=10)
    except (ConfigError, GmailError) as e:
        await update.message.reply_text(t("unread.error", lang, error=e))
        return

    if not messages:
        await update.message.reply_text(t("unread.none", lang))
        return

    lines = [
        t("unread.item", lang,
          account=msg.account,
          sender=msg.sender,
          subject=msg.subject,
          snippet=msg.snippet[:80])
        for msg in messages
    ]
    await update.message.reply_text("\n".join(lines)[:_MAX_MSG])


async def handle_latest(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(ctx)
    try:
        nina = GmailMultiClient.from_env()
    except (ConfigError, GmailError) as e:
        await update.message.reply_text(t("latest.error", lang, error=e))
        return

    lines = []
    for account in nina.accounts:
        msgs = nina.client(account).list_latest(max_results=5)
        lines.append(f"── {account}")
        for msg in msgs:
            mark = "●" if not msg.is_read else " "
            lines.append(f"{mark} {msg.date}")
            lines.append(f"  {t('latest.from', lang, sender=msg.sender)}")
            lines.append(f"  {t('latest.subject', lang, subject=msg.subject)}")
            lines.append("")

    await update.message.reply_text(
        "\n".join(lines)[:_MAX_MSG] or t("latest.none", lang)
    )


async def handle_events(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(ctx)
    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    accounts = discover_accounts(tokens_dir)

    if not accounts:
        await update.message.reply_text(t("events.no_accounts", lang))
        return

    lines = []
    for account in accounts:
        try:
            events = CalendarClient(account, tokens_dir).list_upcoming(max_results=5)
            lines.append(f"── {account}")
            if not events:
                lines.append(f"  {t('events.none', lang)}")
            for ev in events:
                lines.append(f"  {ev.start}")
                lines.append(f"  {ev.title}")
                if ev.location:
                    lines.append(f"  {t('events.location', lang, location=ev.location)}")
                lines.append("")
        except CalendarError as e:
            lines.append(t("events.error", lang, account=account, error=e))

    await update.message.reply_text(
        "\n".join(lines)[:_MAX_MSG] or t("events.not_found", lang)
    )


async def handle_dialogs(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(ctx)
    try:
        with TgClient.from_env() as tg:
            dialogs = tg.list_dialogs(max_results=15)
    except TelegramError as e:
        await update.message.reply_text(t("dialogs.error", lang, error=e))
        return

    lines = []
    for d in dialogs:
        unread = t("dialogs.unread", lang, count=d.unread_count) if d.unread_count else ""
        lines.append(f"[{d.kind}] {d.name}{unread}")

    await update.message.reply_text(
        "\n".join(lines)[:_MAX_MSG] or t("dialogs.none", lang)
    )


# ---------------------------------------------------------------------------
# Nina-state handlers (presence, health, workdays, context)
# ---------------------------------------------------------------------------

async def handle_presence(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from nina.presence.models import PresenceStatus, PresenceState
    from nina.presence.store import load as load_presence, save as save_presence
    lang = _lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]

    if not ctx.args:
        state = load_presence(data_dir)
        since = state.since.strftime("%Y-%m-%d %H:%M")
        note = f"\n{state.note}" if state.note else ""
        label = t(f"presence.label.{state.status.value}", lang)
        await update.message.reply_text(
            t("presence.current", lang, status=state.status.value, label=label, since=since, note=note)
        )
    else:
        status_str = ctx.args[0].lower()
        try:
            status = PresenceStatus(status_str)
        except ValueError:
            valid = " | ".join(s.value for s in PresenceStatus)
            await update.message.reply_text(t("presence.invalid", lang, valid=valid))
            return
        note = " ".join(ctx.args[1:])
        save_presence(PresenceState(status=status, note=note), data_dir)
        label = t(f"presence.label.{status.value}", lang)
        await update.message.reply_text(t("presence.set_ok", lang, status=status.value, label=label))


async def handle_health(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    import time as _time
    lang = _lang(ctx)
    start_time: float = ctx.bot_data["start_time"]
    uptime = int(_time.time() - start_time)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    await update.message.reply_text(
        t("health.online", lang, uptime=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    )


async def handle_workdays(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]
    from nina.workdays.store import load as load_workdays
    schedule = load_workdays(data_dir)
    lines = [t("workdays.timezone", lang, tz=schedule.timezone), ""]
    for d in schedule.days:
        name = t(f"day.{d.day}", lang)
        if d.active and d.start and d.end:
            hours = t("workdays.hours", lang, start=d.start.strftime("%H:%M"), end=d.end.strftime("%H:%M"))
            lines.append(f"{name:<10}  {hours}")
        else:
            lines.append(f"{name:<10}  {t('workdays.off', lang)}")
    await update.message.reply_text("\n".join(lines))


async def handle_timezone(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    from nina.workdays.store import load as load_workdays, save as save_workdays
    lang = _lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]

    if not ctx.args:
        schedule = load_workdays(data_dir)
        await update.message.reply_text(t("workdays.timezone", lang, tz=schedule.timezone))
        return

    tz_str = ctx.args[0]
    try:
        ZoneInfo(tz_str)
    except (ZoneInfoNotFoundError, KeyError):
        await update.message.reply_text(t("workdays.timezone_invalid", lang, tz=tz_str))
        return

    schedule = load_workdays(data_dir)
    schedule.timezone = tz_str
    save_workdays(schedule, data_dir)
    await update.message.reply_text(t("workdays.timezone_set", lang, tz=tz_str))


async def handle_context(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from nina.presence.store import load as load_presence
    from nina.workdays.checker import get_context
    from nina.workdays.store import load as load_workdays
    lang = _lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]
    context = get_context(load_workdays(data_dir), load_presence(data_dir), lang)
    flags = []
    if context.overtime:
        flags.append(t("context.flag.overtime", lang))
    if context.weekend_work:
        flags.append(t("context.flag.weekend", lang))
    flags_str = f" [{', '.join(flags)}]" if flags else ""
    work = t("context.in_work_time" if context.is_work_time else "context.off_hours", lang)
    await update.message.reply_text(f"{context.label}{flags_str}\n{work} · {context.presence_status}")


async def handle_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from nina.presence.models import PresenceStatus
    from nina.profile.store import load as load_profile
    lang = _lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]
    profile = load_profile(data_dir)

    # Filter to specific presence if arg given
    statuses = list(PresenceStatus)
    if ctx.args:
        try:
            statuses = [PresenceStatus(ctx.args[0].lower())]
        except ValueError:
            pass

    if profile.is_empty():
        await update.message.reply_text(t("profile.empty", lang))
        return

    lines = [t("profile.title", lang)]
    for status in statuses:
        p = profile.for_presence(status)
        label = t(f"presence.label.{status.value}", lang)
        lines.append(f"\n{status.value} — {label}")
        if p.gmail:
            lines.append(f"  {t('profile.gmail', lang, accounts=', '.join(p.gmail))}")
        if p.calendar:
            lines.append(f"  {t('profile.calendar', lang, accounts=', '.join(p.calendar))}")
        if not p.gmail and not p.calendar:
            lines.append(f"  {t('profile.no_accounts', lang)}")

    await update.message.reply_text("\n".join(lines))


async def handle_notify(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from nina.notifications.store import load as load_notif, save as save_notif
    lang = _lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]
    args = ctx.args or []

    state = load_notif(data_dir)
    if not args:
        await update.message.reply_text(
            t("notify.config", lang,
              reminder_minutes=state.config.reminder_minutes,
              watch_days=state.config.watch_days)
        )
        return

    try:
        if args[0] == "reminder" and len(args) == 2:
            val = int(args[1])
            if val <= 0:
                raise ValueError
            state.config.reminder_minutes = val
            save_notif(state, data_dir)
            await update.message.reply_text(t("notify.reminder_set", lang, minutes=val))
        elif args[0] == "days" and len(args) == 2:
            val = int(args[1])
            if val <= 0:
                raise ValueError
            state.config.watch_days = val
            save_notif(state, data_dir)
            await update.message.reply_text(t("notify.days_set", lang, days=val))
        else:
            await update.message.reply_text(t("notify.usage", lang))
    except ValueError:
        raw = args[1] if len(args) > 1 else ""
        await update.message.reply_text(t("notify.invalid_value", lang, value=raw))


async def handle_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from nina.errors import CalendarError
    from nina.google.calendar.blocking import execute as execute_blocking, BlockingIntent
    from nina.google.calendar.schedule_parser import parse as parse_schedule
    from nina.presence.store import load as load_presence
    from nina.profile.store import load as load_profile
    from nina.workdays.store import load as load_workdays
    lang = _lang(ctx)
    tokens_dir: Path = ctx.bot_data["tokens_dir"]
    data_dir: Path = ctx.bot_data["data_dir"]
    arg = " ".join(ctx.args) if ctx.args else ""
    if not arg.strip():
        await update.message.reply_text(t("schedule.parse_error", lang))
        return
    schedule = load_workdays(data_dir)
    tz = ZoneInfo(schedule.timezone)
    now = datetime.now(tz)
    parsed = parse_schedule(arg, now)
    if parsed is None:
        await update.message.reply_text(t("schedule.parse_error", lang))
        return
    presence = load_presence(data_dir)
    profile = load_profile(data_dir)
    cal_accounts = profile.for_presence(presence.status).calendar
    if not cal_accounts:
        await update.message.reply_text(t("schedule.no_account", lang))
        return
    intent = BlockingIntent(
        action="block_calendar",
        title=parsed.title,
        duration_minutes=parsed.duration_minutes,
        start_time=parsed.start.strftime("%H:%M"),
    )
    try:
        result = execute_blocking(
            intent,
            account=cal_accounts[0],
            tokens_dir=tokens_dir,
            tz_name=schedule.timezone,
        )
    except CalendarError as e:
        await update.message.reply_text(f"✗ {e}")
        return
    time_fmt = "%H:%M"
    msg = t("schedule.created", lang, title=result.event_title,
            start=result.start.strftime(time_fmt), end=result.end.strftime(time_fmt),
            account=cal_accounts[0])
    if result.link:
        msg += f"\n{result.link}"
    if result.conflicts:
        msg += f"\n{t('schedule.conflict', lang, titles=', '.join(result.conflicts))}"
    await update.message.reply_text(msg)


async def handle_memo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from nina.store.db import open_db
    from nina.store.models import Memo
    from nina.store.repos import memo as memo_repo
    lang = _lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]
    args = ctx.args or []

    conn = open_db(data_dir)

    if not args:
        await update.message.reply_text(t("memo.usage", lang))
        return

    if args[0] == "done" and len(args) >= 2:
        prefix = args[1]
        memos = [m for m in memo_repo.list_all(conn) if m.id.startswith(prefix)]
        if not memos:
            await update.message.reply_text(t("memo.not_found", lang))
            return
        memo_repo.done(conn, memos[0].id)
        await update.message.reply_text(t("memo.done", lang))
        return

    if args[0] == "dismiss" and len(args) >= 2:
        prefix = args[1]
        memos = [m for m in memo_repo.list_all(conn) if m.id.startswith(prefix)]
        if not memos:
            await update.message.reply_text(t("memo.not_found", lang))
            return
        memo_repo.dismiss(conn, memos[0].id)
        await update.message.reply_text(t("memo.dismissed", lang))
        return

    # /memo <text> [due <date>]
    full_text = " ".join(args)
    text_parts = full_text.split(" due ", 1)
    text = text_parts[0].strip()
    due_date = text_parts[1].strip() if len(text_parts) > 1 else None
    memo_repo.add(conn, Memo(text=text, due_date=due_date))
    await update.message.reply_text(t("memo.saved", lang))


async def handle_memos(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from nina.store.db import open_db
    from nina.store.repos import memo as memo_repo
    lang = _lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]
    conn = open_db(data_dir)
    memos = memo_repo.list_open(conn)
    if not memos:
        await update.message.reply_text(t("memo.none_open", lang))
        return
    lines = []
    for m in memos:
        due = t("memo.due", lang, date=m.due_date) if m.due_date else ""
        short_id = m.id[:8]
        lines.append(f"[{short_id}] {m.text}{due}")
    await update.message.reply_text("\n".join(lines))


async def handle_obsidian(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]
    tokens_dir: Path = ctx.bot_data["tokens_dir"]
    from nina.obsidian import vault_path
    if vault_path() is None:
        await update.message.reply_text(t("obsidian.not_set", lang))
        return
    from nina.scheduler.jobs.obsidian_sync import make_job
    make_job(tokens_dir, data_dir)()
    await update.message.reply_text(t("obsidian.done", lang, path=str(vault_path())))


async def handle_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]

    if not ctx.args:
        await update.message.reply_text(t("lang.current", lang, code=lang))
        return

    new_lang = ctx.args[0].lower()
    if new_lang not in SUPPORTED:
        supported = " | ".join(sorted(SUPPORTED))
        await update.message.reply_text(t("lang.invalid", lang, code=new_lang, supported=supported))
        return

    save_locale(LocaleConfig(lang=new_lang), data_dir)
    ctx.bot_data["lang"] = new_lang
    await _set_commands(ctx.application, new_lang)
    await update.message.reply_text(t("lang.set_ok", new_lang, code=new_lang))


# ---------------------------------------------------------------------------
# Obsidian action from natural language
# ---------------------------------------------------------------------------

def _execute_obsidian_intent_text(lang: str, tokens_dir: Path, data_dir: Path) -> str:
    from nina.obsidian import vault_path
    if vault_path() is None:
        return t("obsidian.not_set", lang)
    from nina.scheduler.jobs.obsidian_sync import make_job
    make_job(tokens_dir, data_dir)()
    return t("obsidian.done", lang, path=str(vault_path()))


# ---------------------------------------------------------------------------
# Notification action from natural language
# ---------------------------------------------------------------------------

def _execute_notification_intent_text(
    action: str, minutes: int | None, days: int | None, lang: str, data_dir: Path
) -> str:
    from nina.notifications.store import load as load_notif, save as save_notif
    state = load_notif(data_dir)
    if action == "get":
        return t("notify.config", lang, reminder_minutes=state.config.reminder_minutes, watch_days=state.config.watch_days)
    if action == "set_reminder" and minutes is not None:
        state.config.reminder_minutes = minutes
        save_notif(state, data_dir)
        return t("notify.reminder_set", lang, minutes=minutes)
    if action == "set_days" and days is not None:
        state.config.watch_days = days
        save_notif(state, data_dir)
        return t("notify.days_set", lang, days=days)
    return t("notify.usage", lang)


# ---------------------------------------------------------------------------
# Calendar action from natural language
# ---------------------------------------------------------------------------

def _execute_calendar_intent_text(action: str, lang: str, tokens_dir: Path, data_dir: Path) -> str:
    from nina.errors import CalendarError
    from nina.google.calendar.client import CalendarClient
    from nina.presence.store import load as load_presence
    from nina.profile.store import load as load_profile
    if action == "list":
        presence = load_presence(data_dir)
        profile = load_profile(data_dir)
        cal_accounts = profile.for_presence(presence.status).calendar
        if not cal_accounts:
            return t("blocking.no_account", lang)
        try:
            client = CalendarClient(cal_accounts[0], tokens_dir)
            events = client.list_upcoming(max_results=10)
        except CalendarError as e:
            return f"✗ {e}"
        if not events:
            return t("calendar.no_events", lang)
        lines = []
        for ev in events:
            start = ev.start.strftime("%d/%m %H:%M")
            lines.append(f"{start}  {ev.title}")
        return "\n".join(lines)
    return ""


# ---------------------------------------------------------------------------
# Memo action from natural language (no LLM)
# ---------------------------------------------------------------------------

def _execute_memo_intent_text(action: str, subject: str, lang: str, data_dir: Path) -> str:
    from nina.store.db import open_db
    from nina.store.repos import memo as memo_repo
    conn = open_db(data_dir)
    if action == "list":
        memos = memo_repo.list_open(conn)
        if not memos:
            return t("memo.none_open", lang)
        lines = []
        for m in memos:
            due = t("memo.due", lang, date=m.due_date) if m.due_date else ""
            lines.append(f"[{m.id[:8]}] {m.text}{due}")
        return "\n".join(lines)
    matches = [m for m in memo_repo.list_open(conn) if subject.lower() in m.text.lower()]
    if not matches:
        return t("memo.not_found", lang)
    lines = []
    for m in matches:
        if action == "close":
            memo_repo.done(conn, m.id)
            lines.append(f"{t('memo.done', lang)} — {m.text}")
        elif action == "dismiss":
            memo_repo.dismiss(conn, m.id)
            lines.append(f"{t('memo.dismissed', lang)} — {m.text}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Free-text handler (LLM interpreter)
# ---------------------------------------------------------------------------

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from nina.errors import CalendarError, LLMError

    lang = _lang(ctx)
    tokens_dir: Path = ctx.bot_data["tokens_dir"]
    data_dir: Path = ctx.bot_data["data_dir"]
    text = update.message.text or ""

    # Layer 1 — pattern match, zero LLM calls
    from nina.memo.interpreter import try_action as memo_try
    result = memo_try(text, lang)
    if result:
        await update.message.reply_text(
            _execute_memo_intent_text(result.action, result.subject, lang, data_dir)
        )
        return

    from nina.google.calendar.interpreter import try_action as cal_try
    cal_result = cal_try(text, lang)
    if cal_result:
        await update.message.reply_text(
            _execute_calendar_intent_text(cal_result.action, lang, tokens_dir, data_dir)
        )
        return

    from nina.obsidian.interpreter import try_action as obsidian_try
    if obsidian_try(text, lang):
        await update.message.reply_text(
            _execute_obsidian_intent_text(lang, tokens_dir, data_dir)
        )
        return

    from nina.notifications.interpreter import try_action as notif_try
    notif_result = notif_try(text, lang)
    if notif_result:
        await update.message.reply_text(
            _execute_notification_intent_text(notif_result.action, notif_result.minutes, notif_result.days, lang, data_dir)
        )
        return

    # Keyword gates — determine candidates without calling LLM
    from nina.google.calendar.blocking import has_time_signal
    from nina.google.calendar.interpreter import has_context as cal_has
    from nina.notifications.interpreter import has_context as notif_has
    from nina.obsidian.interpreter import has_context as obsidian_has
    from nina.presence.interpreter import has_context as presence_has
    from nina.profile.interpreter import has_context as profile_has
    from nina.workdays.interpreter import has_context as schedule_has

    candidates: set[str] = set()
    if "memo" in text.lower():
        candidates.add("memo")
    if cal_has(text, lang):
        candidates.add("calendar")
    if has_time_signal(text):
        candidates.add("blocking")
    if presence_has(text, lang):
        candidates.add("presence")
    if schedule_has(text, lang):
        candidates.add("schedule")
    if profile_has(text, lang):
        candidates.add("profile")
    if obsidian_has(text, lang):
        candidates.add("obsidian")
    if notif_has(text, lang):
        candidates.add("notifications")

    # Load LLM once
    try:
        from nina.llm.client import LLMClient
        llm = LLMClient.from_env()
    except (LLMError, Exception):
        await update.message.reply_text(t("llm.unavailable", lang))
        return

    # If no keyword gate fired, ask router LLM to classify
    if not candidates:
        from nina.intent.router import route
        domain = route(text, llm).domain
        if domain == "none":
            await update.message.reply_text(t("llm.not_understood", lang))
            return
        candidates = {domain}

    # Execute candidates in priority order
    from nina.google.calendar.blocking import execute as execute_blocking
    from nina.google.calendar.blocking import interpret as interpret_blocking
    from nina.presence.interpreter import interpret as interpret_presence
    from nina.presence.models import PresenceState
    from nina.presence.store import load as load_presence, save as save_presence
    from nina.profile.interpreter import apply as apply_profile
    from nina.profile.interpreter import interpret as interpret_profile
    from nina.profile.store import load as load_profile, save as save_profile
    from nina.workdays.interpreter import apply as apply_schedule
    from nina.workdays.interpreter import interpret as interpret_schedule
    from nina.workdays.store import load as load_workdays, save as save_workdays
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if "memo" in candidates:
        from nina.memo.interpreter import interpret as memo_interpret
        memo_intent = memo_interpret(text, llm)
        if memo_intent.action != "none":
            await update.message.reply_text(
                _execute_memo_intent_text(memo_intent.action, memo_intent.subject, lang, data_dir)
            )
            return

    if "calendar" in candidates:
        from nina.google.calendar.interpreter import interpret as cal_interpret
        cal_intent = cal_interpret(text, llm, lang)
        if cal_intent.action != "none":
            await update.message.reply_text(
                _execute_calendar_intent_text(cal_intent.action, lang, tokens_dir, data_dir)
            )
            return

    if "blocking" in candidates:
        _schedule_pre = load_workdays(data_dir)
        _now = datetime.now(ZoneInfo(_schedule_pre.timezone))
        blocking_intents = interpret_blocking(text, llm, now=_now)
        if blocking_intents:
            presence = load_presence(data_dir)
            profile = load_profile(data_dir)
            cal_accounts = profile.for_presence(presence.status).calendar
            if not cal_accounts:
                await update.message.reply_text(t("blocking.no_account", lang))
                return
            time_fmt = "%H:%M"
            for blocking_intent in blocking_intents:
                try:
                    result = execute_blocking(
                        blocking_intent,
                        account=cal_accounts[0],
                        tokens_dir=tokens_dir,
                        tz_name=_schedule_pre.timezone,
                    )
                except CalendarError as e:
                    await update.message.reply_text(f"✗ {e}")
                    continue
                reply = t("blocking.created", lang,
                          title=result.event_title,
                          start=result.start.strftime(time_fmt),
                          end=result.end.strftime(time_fmt),
                          account=cal_accounts[0])
                if result.link:
                    reply += f"\n{result.link}"
                if result.conflicts:
                    reply += "\n" + t("blocking.conflict", lang, titles=", ".join(result.conflicts))
                await update.message.reply_text(reply)
            return

    if "presence" in candidates:
        presence_intent = interpret_presence(text, llm)
        if presence_intent.action == "set_presence" and presence_intent.status is not None:
            save_presence(PresenceState(status=presence_intent.status, note=presence_intent.note), data_dir)
            label = t(f"presence.label.{presence_intent.status.value}", lang)
            await update.message.reply_text(
                t("llm.presence_set", lang, status=presence_intent.status.value, label=label)
            )
            return

    if "schedule" in candidates:
        schedule_intent = interpret_schedule(text, llm)
        if schedule_intent.action == "update_schedule":
            schedule = load_workdays(data_dir)
            save_workdays(apply_schedule(schedule_intent, schedule), data_dir)
            await update.message.reply_text(t("llm.schedule_set", lang))
            return

    if "profile" in candidates:
        profile_intent = interpret_profile(text, llm)
        if profile_intent.action == "update_profile":
            profile = load_profile(data_dir)
            save_profile(apply_profile(profile_intent, profile), data_dir)
            await update.message.reply_text(t("profile.set_ok", lang))
            return

    if "obsidian" in candidates:
        await update.message.reply_text(
            _execute_obsidian_intent_text(lang, tokens_dir, data_dir)
        )
        return

    if "notifications" in candidates:
        from nina.notifications.interpreter import interpret as notif_interpret
        notif_intent = notif_interpret(text, llm)
        if notif_intent.action != "none":
            await update.message.reply_text(
                _execute_notification_intent_text(notif_intent.action, notif_intent.minutes, notif_intent.days, lang, data_dir)
            )
            return

    await update.message.reply_text(t("llm.not_understood", lang))


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_application(token: str, owner_id: int, tokens_dir: Path, data_dir: Path, sessions_dir: Path) -> Application:
    """Build a persistent PTB Application restricted to owner_id."""
    import time as _time
    owner_filter = filters.Chat(owner_id)

    async def _post_init(application: Application) -> None:
        await _set_commands(application, application.bot_data["lang"])

    app = Application.builder().token(token).post_init(_post_init).build()
    app.bot_data["tokens_dir"] = tokens_dir
    app.bot_data["data_dir"] = data_dir
    app.bot_data["sessions_dir"] = sessions_dir
    app.bot_data["owner_id"] = owner_id
    app.bot_data["start_time"] = _time.time()
    app.bot_data["lang"] = load_locale(data_dir).lang

    app.add_handler(CommandHandler("start",    handle_start,    filters=owner_filter))
    app.add_handler(CommandHandler("help",     handle_help,     filters=owner_filter))
    app.add_handler(CommandHandler("lang",     handle_lang,     filters=owner_filter))
    app.add_handler(CommandHandler("presence", handle_presence, filters=owner_filter))
    app.add_handler(CommandHandler("health",   handle_health,   filters=owner_filter))
    app.add_handler(CommandHandler("workdays",  handle_workdays,  filters=owner_filter))
    app.add_handler(CommandHandler("timezone",  handle_timezone,  filters=owner_filter))
    app.add_handler(CommandHandler("context",   handle_context,   filters=owner_filter))
    app.add_handler(CommandHandler("profile",   handle_profile,   filters=owner_filter))
    app.add_handler(CommandHandler("schedule",  handle_schedule,  filters=owner_filter))
    app.add_handler(CommandHandler("notify",    handle_notify,    filters=owner_filter))
    app.add_handler(CommandHandler("memo",      handle_memo,      filters=owner_filter))
    app.add_handler(CommandHandler("memos",     handle_memos,     filters=owner_filter))
    app.add_handler(CommandHandler("obsidian",  handle_obsidian,  filters=owner_filter))
    app.add_handler(MessageHandler(owner_filter & filters.TEXT & ~filters.COMMAND, handle_message))
    return app


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

async def run_batch(token: str, owner_id: int, sessions_dir: Path) -> int:
    """Fetch pending bot updates, process each one, persist offset, return count."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("unread", handle_unread))
    app.add_handler(CommandHandler("latest", handle_latest))
    app.add_handler(CommandHandler("events", handle_events))
    app.add_handler(CommandHandler("dialogs", handle_dialogs))

    offset = load_offset(sessions_dir)
    processed = 0

    async with app:
        updates = await app.bot.get_updates(offset=offset, timeout=0, limit=100)

        for update in updates:
            chat_id = update.message.chat_id if update.message else None
            if chat_id == owner_id:
                await app.process_update(update)
                processed += 1

        if updates:
            save_offset(sessions_dir, updates[-1].update_id + 1)

    return processed


async def _fetch_senders(token: str) -> list[dict]:  # type: ignore[type-arg]
    """Return a list of unique senders from pending updates (no offset change)."""
    app = Application.builder().token(token).build()
    async with app:
        updates = await app.bot.get_updates(timeout=0, limit=100)
    seen: dict[int, dict] = {}  # type: ignore[type-arg]
    for u in updates:
        if u.message:
            cid = u.message.chat_id
            if cid not in seen:
                seen[cid] = {
                    "chat_id": cid,
                    "name": u.message.chat.full_name or u.message.chat.username or "?",
                    "username": u.message.chat.username or "",
                }
    return list(seen.values())


def setup_from_env(env_file: Path | None = None) -> None:
    """Discover who has messaged the bot and print their chat IDs."""
    load_dotenv(env_file)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise TelegramError(
            "TELEGRAM_BOT_TOKEN not set in .env\n"
            "Create a bot with @BotFather and set the token first."
        )

    senders = asyncio.run(_fetch_senders(token))

    if not senders:
        print("No messages found yet.")
        print("Send any message (e.g. /start) to your bot in Telegram, then run again.")
        return

    print("People who have messaged your bot:\n")
    for s in senders:
        username = f"  @{s['username']}" if s["username"] else ""
        print(f"  chat_id: {s['chat_id']}  —  {s['name']}{username}")

    print("\nCopy your chat_id to .env:")
    print("  TELEGRAM_OWNER_ID=<your chat_id>")


def run_batch_from_env(env_file: Path | None = None) -> int:
    """Load configuration from .env and run the batch processor."""
    load_dotenv(env_file)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    owner_raw = os.environ.get("TELEGRAM_OWNER_ID", "")

    if not token:
        raise TelegramError(
            "TELEGRAM_BOT_TOKEN not set in .env\n"
            "Steps:\n"
            "  1. Open Telegram and talk to @BotFather\n"
            "  2. Send /newbot and follow the prompts\n"
            "  3. Copy the token to .env"
        )
    if not owner_raw:
        raise TelegramError(
            "TELEGRAM_OWNER_ID not set in .env\n"
            "Steps:\n"
            "  1. Start the bot: make tg-bot\n"
            "  2. Send /start to your bot in Telegram\n"
            "  3. Run make tg-bot again — it will print your chat ID\n"
            "  4. Copy that number to TELEGRAM_OWNER_ID in .env"
        )

    try:
        owner_id = int(owner_raw)
    except ValueError:
        raise TelegramError(
            f"TELEGRAM_OWNER_ID must be a number, got: {owner_raw!r}"
        )

    sessions_dir = Path(os.environ.get("SESSIONS_DIR", "sessions"))
    return asyncio.run(run_batch(token, owner_id, sessions_dir))
