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

def _offset_file(tokens_dir: Path) -> Path:
    return tokens_dir / "bot_offset.txt"


def load_offset(tokens_dir: Path) -> int:
    """Return the stored update offset, or 0 if not yet set."""
    f = _offset_file(tokens_dir)
    return int(f.read_text().strip()) if f.exists() else 0


def save_offset(tokens_dir: Path, offset: int) -> None:
    """Persist the next offset so the next run skips already-processed updates."""
    tokens_dir.mkdir(parents=True, exist_ok=True)
    _offset_file(tokens_dir).write_text(str(offset))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.bot_data.get("lang", "pt")


_COMMAND_NAMES = [
    "start", "help", "lang", "presence", "health",
    "workdays", "timezone", "context", "unread", "latest", "events", "dialogs",
]


async def _set_commands(app: Application, lang: str) -> None:
    """Register localized command descriptions with Telegram."""
    commands = [BotCommand(name, t(f"cmd.{name}", lang)) for name in _COMMAND_NAMES]
    await app.bot.set_my_commands(commands)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def handle_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    tokens_dir: Path = ctx.bot_data["tokens_dir"]
    tg_lang_code = (update.effective_user.language_code or "") if update.effective_user else ""

    # Auto-detect language on first /start if not yet saved
    locale = load_locale(tokens_dir)
    if tg_lang_code:
        detected = tg_lang_code.split("-")[0].lower()
        if detected in SUPPORTED and detected != locale.lang:
            locale = LocaleConfig(lang=detected)
            save_locale(locale, tokens_dir)
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
    tokens_dir: Path = ctx.bot_data["tokens_dir"]

    if not ctx.args:
        state = load_presence(tokens_dir)
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
        save_presence(PresenceState(status=status, note=note), tokens_dir)
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
    tokens_dir: Path = ctx.bot_data["tokens_dir"]
    from nina.workdays.store import load as load_workdays
    schedule = load_workdays(tokens_dir)
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
    tokens_dir: Path = ctx.bot_data["tokens_dir"]

    if not ctx.args:
        schedule = load_workdays(tokens_dir)
        await update.message.reply_text(t("workdays.timezone", lang, tz=schedule.timezone))
        return

    tz_str = ctx.args[0]
    try:
        ZoneInfo(tz_str)
    except (ZoneInfoNotFoundError, KeyError):
        await update.message.reply_text(t("workdays.timezone_invalid", lang, tz=tz_str))
        return

    schedule = load_workdays(tokens_dir)
    schedule.timezone = tz_str
    save_workdays(schedule, tokens_dir)
    await update.message.reply_text(t("workdays.timezone_set", lang, tz=tz_str))


async def handle_context(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from nina.presence.store import load as load_presence
    from nina.workdays.checker import get_context
    from nina.workdays.store import load as load_workdays
    lang = _lang(ctx)
    tokens_dir: Path = ctx.bot_data["tokens_dir"]
    context = get_context(load_workdays(tokens_dir), load_presence(tokens_dir), lang)
    flags = []
    if context.overtime:
        flags.append(t("context.flag.overtime", lang))
    if context.weekend_work:
        flags.append(t("context.flag.weekend", lang))
    flags_str = f" [{', '.join(flags)}]" if flags else ""
    work = t("context.in_work_time" if context.is_work_time else "context.off_hours", lang)
    await update.message.reply_text(f"{context.label}{flags_str}\n{work} · {context.presence_status}")


async def handle_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(ctx)
    tokens_dir: Path = ctx.bot_data["tokens_dir"]

    if not ctx.args:
        await update.message.reply_text(t("lang.current", lang, code=lang))
        return

    new_lang = ctx.args[0].lower()
    if new_lang not in SUPPORTED:
        supported = " | ".join(sorted(SUPPORTED))
        await update.message.reply_text(t("lang.invalid", lang, code=new_lang, supported=supported))
        return

    save_locale(LocaleConfig(lang=new_lang), tokens_dir)
    ctx.bot_data["lang"] = new_lang
    await _set_commands(ctx.application, new_lang)
    await update.message.reply_text(t("lang.set_ok", new_lang, code=new_lang))


# ---------------------------------------------------------------------------
# Free-text handler (LLM interpreter)
# ---------------------------------------------------------------------------

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from nina.errors import LLMError
    from nina.llm.client import LLMClient
    from nina.presence.interpreter import interpret as interpret_presence
    from nina.presence.models import PresenceState
    from nina.presence.store import save as save_presence
    from nina.workdays.interpreter import apply as apply_schedule
    from nina.workdays.interpreter import interpret as interpret_schedule
    from nina.workdays.store import load as load_workdays, save as save_workdays

    lang = _lang(ctx)
    tokens_dir: Path = ctx.bot_data["tokens_dir"]
    text = update.message.text or ""

    try:
        llm = LLMClient.from_env()
    except LLMError:
        await update.message.reply_text(t("llm.unavailable", lang))
        return

    # Try presence first
    presence_intent = interpret_presence(text, llm)
    if presence_intent.action == "set_presence" and presence_intent.status is not None:
        save_presence(PresenceState(status=presence_intent.status, note=presence_intent.note), tokens_dir)
        label = t(f"presence.label.{presence_intent.status.value}", lang)
        await update.message.reply_text(
            t("llm.presence_set", lang, status=presence_intent.status.value, label=label)
        )
        return

    # Try schedule
    schedule_intent = interpret_schedule(text, llm)
    if schedule_intent.action == "update_schedule":
        schedule = load_workdays(tokens_dir)
        save_workdays(apply_schedule(schedule_intent, schedule), tokens_dir)
        await update.message.reply_text(t("llm.schedule_set", lang))
        return

    await update.message.reply_text(t("llm.not_understood", lang))


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_application(token: str, owner_id: int, tokens_dir: Path) -> Application:
    """Build a persistent PTB Application restricted to owner_id."""
    import time as _time
    owner_filter = filters.Chat(owner_id)

    async def _post_init(application: Application) -> None:
        await _set_commands(application, application.bot_data["lang"])

    app = Application.builder().token(token).post_init(_post_init).build()
    app.bot_data["tokens_dir"] = tokens_dir
    app.bot_data["owner_id"] = owner_id
    app.bot_data["start_time"] = _time.time()
    app.bot_data["lang"] = load_locale(tokens_dir).lang

    app.add_handler(CommandHandler("start",    handle_start,    filters=owner_filter))
    app.add_handler(CommandHandler("help",     handle_help,     filters=owner_filter))
    app.add_handler(CommandHandler("lang",     handle_lang,     filters=owner_filter))
    app.add_handler(CommandHandler("presence", handle_presence, filters=owner_filter))
    app.add_handler(CommandHandler("health",   handle_health,   filters=owner_filter))
    app.add_handler(CommandHandler("workdays",  handle_workdays,  filters=owner_filter))
    app.add_handler(CommandHandler("timezone",  handle_timezone,  filters=owner_filter))
    app.add_handler(CommandHandler("context",   handle_context,   filters=owner_filter))
    app.add_handler(CommandHandler("unread",   handle_unread,   filters=owner_filter))
    app.add_handler(CommandHandler("latest",   handle_latest,   filters=owner_filter))
    app.add_handler(CommandHandler("events",   handle_events,   filters=owner_filter))
    app.add_handler(CommandHandler("dialogs",  handle_dialogs,  filters=owner_filter))
    app.add_handler(MessageHandler(owner_filter & filters.TEXT & ~filters.COMMAND, handle_message))
    return app


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

async def run_batch(token: str, owner_id: int, tokens_dir: Path) -> int:
    """Fetch pending bot updates, process each one, persist offset, return count."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("unread", handle_unread))
    app.add_handler(CommandHandler("latest", handle_latest))
    app.add_handler(CommandHandler("events", handle_events))
    app.add_handler(CommandHandler("dialogs", handle_dialogs))

    offset = load_offset(tokens_dir)
    processed = 0

    async with app:
        updates = await app.bot.get_updates(offset=offset, timeout=0, limit=100)

        for update in updates:
            chat_id = update.message.chat_id if update.message else None
            if chat_id == owner_id:
                await app.process_update(update)
                processed += 1

        if updates:
            save_offset(tokens_dir, updates[-1].update_id + 1)

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

    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    return asyncio.run(run_batch(token, owner_id, tokens_dir))
