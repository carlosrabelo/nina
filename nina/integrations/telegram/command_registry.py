"""Registered slash-command names and localized /setMyCommands."""

from telegram import BotCommand
from telegram.ext import Application, ContextTypes

from nina.core.i18n import t

COMMAND_NAMES = [
    "start",
    "help",
    "lang",
    "health",
    "presence",
    "workdays",
    "timezone",
    "context",
    "profile",
    "schedule",
    "notify",
    "memo",
    "memos",
    "gmail_label",
]


def bot_lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.bot_data.get("lang", "pt")


async def set_bot_commands(app: Application, lang: str) -> None:
    """Register localized command descriptions with Telegram."""
    commands = [BotCommand(name, t(f"cmd.{name}", lang)) for name in COMMAND_NAMES]
    await app.bot.set_my_commands(commands)
