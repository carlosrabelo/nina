# telegram_bot.py
"""Telegram Bot — batch mode command processor.

Design: no persistent loop.
Each invocation fetches whatever commands are pending in the bot's queue,
processes them, saves the offset (so they are not processed again), and exits.

Run manually:  ./nina.py tg-bot
Run via cron:  * * * * * /path/to/nina/make/tg-bot.sh
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from auth import discover_accounts
from calendar_client import CalendarClient
from errors import CalendarError, ConfigError, GmailError, TelegramError
from gmail import GmailMultiClient
from telegram_client import TgClient

_MAX_MSG = 4000  # Telegram hard limit is 4096 chars; stay under to be safe


# ---------------------------------------------------------------------------
# Offset persistence
# Tracks the last processed update_id so re-runs never repeat commands.
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
# Command handlers
# ---------------------------------------------------------------------------

async def handle_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Olá! Sou a Nina, sua assistente pessoal.\n\n"
        "Use /help para ver os comandos disponíveis.\n\n"
        f"Seu chat ID: {update.message.chat_id}"
    )


async def handle_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Comandos disponíveis:\n\n"
        "📧 Gmail\n"
        "/unread — emails não lidos\n"
        "/latest — últimos emails recebidos\n\n"
        "📅 Calendar\n"
        "/events — próximos eventos\n\n"
        "💬 Telegram\n"
        "/dialogs — chats recentes\n"
    )


async def handle_unread(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        nina = GmailMultiClient.from_env()
        messages = nina.list_unread(max_results=10)
    except (ConfigError, GmailError) as e:
        await update.message.reply_text(f"Erro: {e}")
        return

    if not messages:
        await update.message.reply_text("Nenhum email não lido.")
        return

    lines = []
    for msg in messages:
        lines.append(
            f"[{msg.account}]\n"
            f"De: {msg.sender}\n"
            f"Assunto: {msg.subject}\n"
            f"Preview: {msg.snippet[:80]}\n"
        )
    await update.message.reply_text("\n".join(lines)[:_MAX_MSG])


async def handle_latest(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        nina = GmailMultiClient.from_env()
    except (ConfigError, GmailError) as e:
        await update.message.reply_text(f"Erro: {e}")
        return

    lines = []
    for account in nina.accounts:
        msgs = nina.client(account).list_latest(max_results=5)
        lines.append(f"── {account}")
        for msg in msgs:
            mark = "●" if not msg.is_read else " "
            lines.append(f"{mark} {msg.date}")
            lines.append(f"  De: {msg.sender}")
            lines.append(f"  Assunto: {msg.subject}")
            lines.append("")

    await update.message.reply_text(
        "\n".join(lines)[:_MAX_MSG] or "Nenhum email encontrado."
    )


async def handle_events(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    accounts = discover_accounts(tokens_dir)

    if not accounts:
        await update.message.reply_text("Nenhuma conta autenticada.")
        return

    lines = []
    for account in accounts:
        try:
            events = CalendarClient(account, tokens_dir).list_upcoming(max_results=5)
            lines.append(f"── {account}")
            if not events:
                lines.append("  (sem eventos próximos)")
            for ev in events:
                lines.append(f"  {ev.start}")
                lines.append(f"  {ev.title}")
                if ev.location:
                    lines.append(f"  Local: {ev.location}")
                lines.append("")
        except CalendarError as e:
            lines.append(f"Erro em {account}: {e}")

    await update.message.reply_text(
        "\n".join(lines)[:_MAX_MSG] or "Nenhum evento encontrado."
    )


async def handle_dialogs(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with TgClient.from_env() as tg:
            dialogs = tg.list_dialogs(max_results=15)
    except TelegramError as e:
        await update.message.reply_text(f"Erro: {e}")
        return

    lines = []
    for d in dialogs:
        unread = f" ({d.unread_count} não lidas)" if d.unread_count else ""
        lines.append(f"[{d.kind}] {d.name}{unread}")

    await update.message.reply_text(
        "\n".join(lines)[:_MAX_MSG] or "Nenhum chat encontrado."
    )


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

async def run_batch(token: str, owner_id: int, tokens_dir: Path) -> int:
    """Fetch pending bot updates, process each one, persist offset, return count.

    Security: updates not originating from *owner_id* are silently skipped.
    This prevents anyone else from querying Nina even if they find the bot.
    """
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
    """Discover who has messaged the bot and print their chat IDs.

    Use this once to find your TELEGRAM_OWNER_ID:
      1. Set TELEGRAM_BOT_TOKEN in .env
      2. Send any message to your bot in Telegram
      3. Run: make tg-bot-setup
      4. Copy your chat ID to TELEGRAM_OWNER_ID in .env
    """
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
    """Load configuration from .env and run the batch processor.

    Required .env variables::

        TELEGRAM_BOT_TOKEN=123456:ABC...   # from BotFather
        TELEGRAM_OWNER_ID=987654321        # your personal chat ID

    Returns the number of commands processed.

    Raises:
        TelegramError: If required config is missing or invalid.
    """
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
