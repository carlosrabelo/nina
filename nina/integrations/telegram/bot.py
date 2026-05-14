"""Telegram Bot — persistent and batch mode."""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from nina.core.i18n import t
from nina.core.locale.models import SUPPORTED, LocaleConfig
from nina.core.locale.store import load as load_locale
from nina.core.locale.store import save as save_locale
from nina.errors import CalendarError, ConfigError, GmailError, TelegramError
from nina.integrations.google.auth import discover_accounts
from nina.integrations.google.calendar.client import CalendarClient
from nina.integrations.google.gmail.client import GmailMultiClient
from nina.integrations.telegram.client import TgClient
from nina.integrations.telegram.command_registry import bot_lang, set_bot_commands
from nina.integrations.telegram.constants import MAX_MSG
from nina.integrations.telegram.free_text_handler import handle_message
from nina.integrations.telegram.offset_store import load_offset, save_offset

log = logging.getLogger(__name__)

# Re-export for tests and backwards compatibility
__all__ = [
    "create_application",
    "load_offset",
    "run_batch",
    "run_batch_from_env",
    "save_offset",
    "setup_from_env",
]


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    import traceback
    from telegram.error import NetworkError, TimedOut
    err = context.error
    if isinstance(err, (NetworkError, TimedOut)):
        log.warning("telegram network error: %s", err)
        return
    log.error("telegram unhandled error: %s\n%s", err, traceback.format_exc())


async def handle_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
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

    lang = bot_lang(ctx)
    await update.message.reply_text(
        t("start.greeting", lang, chat_id=update.message.chat_id)
    )


async def handle_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    lang = bot_lang(ctx)
    topic = (ctx.args[0].lower() if ctx.args else "").strip()
    if topic:
        key = f"help.{topic}"
        from nina.core.i18n import t as _t
        text = _t(key, lang)
        if text == key:
            await update.message.reply_text(t("help.text", lang))
        else:
            await update.message.reply_text(text)
        return
    await update.message.reply_text(t("help.text", lang))


async def handle_unread(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    lang = bot_lang(ctx)
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
    await update.message.reply_text("\n".join(lines)[:MAX_MSG])


async def handle_latest(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    lang = bot_lang(ctx)
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
        "\n".join(lines)[:MAX_MSG] or t("latest.none", lang)
    )


async def handle_events(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    lang = bot_lang(ctx)
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
        "\n".join(lines)[:MAX_MSG] or t("events.not_found", lang)
    )


async def handle_dialogs(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    lang = bot_lang(ctx)
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
        "\n".join(lines)[:MAX_MSG] or t("dialogs.none", lang)
    )


# ---------------------------------------------------------------------------
# Nina-state handlers (presence, health, workdays, context)
# ---------------------------------------------------------------------------

async def handle_presence(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    from nina.skills.presence.models import PresenceState, PresenceStatus
    from nina.skills.presence.store import load as load_presence
    from nina.skills.presence.store import save as save_presence
    lang = bot_lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]

    if not ctx.args:
        state = load_presence(data_dir)
        from zoneinfo import ZoneInfo as _ZI

        from nina.skills.workdays.store import load as _load_wd
        _tz = _ZI(_load_wd(data_dir).timezone)
        since = state.since.astimezone(_tz).strftime("%Y-%m-%d %H:%M")
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
    if update.message is None:
        return
    from nina.skills.health.execute import get_status
    lang = bot_lang(ctx)
    status = get_status()
    await update.message.reply_text(
        t("health.online", lang, uptime=status["uptime"])
    )


async def handle_workdays(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    lang = bot_lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]
    from nina.skills.workdays.store import load as load_workdays
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
    if update.message is None:
        return
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    from nina.skills.workdays.store import load as load_workdays
    from nina.skills.workdays.store import save as save_workdays
    lang = bot_lang(ctx)
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
    if update.message is None:
        return
    from nina.skills.presence.store import load as load_presence
    from nina.skills.workdays.checker import get_context
    from nina.skills.workdays.store import load as load_workdays
    lang = bot_lang(ctx)
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
    if update.message is None:
        return
    from nina.skills.presence.models import PresenceStatus
    from nina.skills.profile.store import load as load_profile
    lang = bot_lang(ctx)
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
    if update.message is None:
        return
    from nina.skills.notifications.store import load as load_notif
    from nina.skills.notifications.store import save as save_notif
    lang = bot_lang(ctx)
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
    if update.message is None:
        return
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from nina.errors import CalendarError
    from nina.skills.calendar.blocking import BlockingIntent
    from nina.skills.calendar.blocking import execute as execute_blocking
    from nina.skills.calendar.schedule_parser import parse as parse_schedule
    from nina.skills.presence.store import load as load_presence
    from nina.skills.profile.store import load as load_profile
    from nina.skills.workdays.store import load as load_workdays
    lang = bot_lang(ctx)
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
    _WEEKDAY_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    _WEEKDAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    time_fmt = "%H:%M"
    _wd = result.start.weekday()
    _day_abbr = (_WEEKDAY_PT[_wd] if lang == "pt" else _WEEKDAY_EN[_wd])
    date_label = f"{_day_abbr}, {result.start.strftime('%d/%m')}"
    msg = t("schedule.created", lang, title=result.event_title,
            date=date_label, start=result.start.strftime(time_fmt),
            end=result.end.strftime(time_fmt), account=cal_accounts[0])
    if result.conflicts:
        msg += f"\n{t('schedule.conflict', lang, titles=', '.join(result.conflicts))}"
    await update.message.reply_text(msg)


async def handle_memo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    from nina.core.store.db import open_db
    from nina.core.store.models import Memo
    from nina.core.store.repos import memo as memo_repo
    lang = bot_lang(ctx)
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
    if update.message is None:
        return
    from nina.core.store.db import open_db
    from nina.core.store.repos import memo as memo_repo
    lang = bot_lang(ctx)
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


async def handle_gmail_label(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    from nina.core.i18n import t
    from nina.skills.gmail_label.execute import (
        add_ignored,
        add_rule_direct,
        check_rules,
        dismiss_all_pending_labels,
        dismiss_pending_by_prefix,
        format_ignored_list,
        format_pending_list,
        remove_ignored,
        scan_pending_suggestions,
        teach_label_for_pending,
    )

    lang = bot_lang(ctx)
    data_dir: Path = ctx.bot_data["data_dir"]
    tokens_dir: Path = ctx.bot_data["tokens_dir"]
    args = ctx.args or []

    if not args:
        text = format_pending_list(data_dir)
        await update.message.reply_text(text[:MAX_MSG])
        return
    if args[0].lower() == "dismiss":
        if len(args) < 2:
            await update.message.reply_text(t("gmail_label.usage", lang))
            return
        out = dismiss_pending_by_prefix(data_dir, args[1])
        await update.message.reply_text(out[:MAX_MSG])
        return
    if args[0].lower() == "dismiss-all":
        out = dismiss_all_pending_labels(data_dir)
        await update.message.reply_text(out[:MAX_MSG])
        return
    if args[0].lower() == "rule":
        if len(args) < 4 or args[1].lower() != "add":
            await update.message.reply_text(t("gmail_label.usage", lang))
            return
        out = add_rule_direct(data_dir, args[2], args[3], " ".join(args[4:]))
        await update.message.reply_text(out[:MAX_MSG])
        return
    if args[0].lower() == "rules":
        if len(args) < 2 or args[1].lower() != "check":
            await update.message.reply_text(t("gmail_label.usage", lang))
            return
        out = check_rules(data_dir, tokens_dir)
        await update.message.reply_text(out[:MAX_MSG])
        return
    if args[0].lower() == "pending":
        if len(args) < 2 or args[1].lower() != "scan":
            await update.message.reply_text(t("gmail_label.usage", lang))
            return
        out = scan_pending_suggestions(data_dir)
        await update.message.reply_text(out[:MAX_MSG])
        return
    if args[0].lower() == "ignore":
        if len(args) < 2 or args[1].lower() not in ("list", "add", "remove"):
            await update.message.reply_text(t("gmail_label.ignore_usage", lang))
            return
        sub = args[1].lower()
        if sub == "list":
            acct = args[2] if len(args) > 2 else None
            out = format_ignored_list(data_dir, account=acct)
            await update.message.reply_text(out[:MAX_MSG])
            return
        if sub == "add":
            if len(args) < 4:
                await update.message.reply_text(t("gmail_label.ignore_usage", lang))
                return
            out = add_ignored(data_dir, args[2], args[3])
            await update.message.reply_text(out[:MAX_MSG])
            return
        if sub == "remove":
            if len(args) < 4:
                await update.message.reply_text(t("gmail_label.ignore_usage", lang))
                return
            out = remove_ignored(data_dir, args[2], args[3])
            await update.message.reply_text(out[:MAX_MSG])
            return
    if len(args) < 2:
        await update.message.reply_text(t("gmail_label.usage", lang))
        return
    pending_prefix = args[0]
    label = " ".join(args[1:])
    out = teach_label_for_pending(tokens_dir, data_dir, pending_prefix, label)
    await update.message.reply_text(out[:MAX_MSG])


async def handle_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    lang = bot_lang(ctx)
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
    await set_bot_commands(ctx.application, new_lang)
    await update.message.reply_text(t("lang.set_ok", new_lang, code=new_lang))


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_application(token: str, owner_id: int, tokens_dir: Path, data_dir: Path, sessions_dir: Path) -> Application:
    """Build a persistent PTB Application restricted to owner_id."""
    import time as _time
    owner_filter = filters.Chat(owner_id)

    async def _post_init(application: Application) -> None:
        await set_bot_commands(application, application.bot_data["lang"])

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
    app.add_handler(CommandHandler("health",   handle_health,   filters=owner_filter))
    app.add_handler(CommandHandler("presence", handle_presence, filters=owner_filter))
    app.add_handler(CommandHandler("workdays",  handle_workdays,  filters=owner_filter))
    app.add_handler(CommandHandler("timezone",  handle_timezone,  filters=owner_filter))
    app.add_handler(CommandHandler("context",   handle_context,   filters=owner_filter))
    app.add_handler(CommandHandler("profile",   handle_profile,   filters=owner_filter))
    app.add_handler(CommandHandler("schedule",  handle_schedule,  filters=owner_filter))
    app.add_handler(CommandHandler("notify",    handle_notify,    filters=owner_filter))
    app.add_handler(CommandHandler("memo",      handle_memo,      filters=owner_filter))
    app.add_handler(CommandHandler("memos",     handle_memos,     filters=owner_filter))
    app.add_handler(CommandHandler("gmail_label", handle_gmail_label, filters=owner_filter))
    app.add_handler(MessageHandler(owner_filter & filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(_error_handler)
    return app


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

async def run_batch(token: str, owner_id: int, sessions_dir: Path) -> int:
    """Fetch pending bot updates, process each one, persist offset, return count."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))

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
            "  1. Start the bot: nina telegram bot\n"
            "  2. Send /start to your bot in Telegram\n"
            "  3. Run nina telegram bot again — it will print your chat ID\n"
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
