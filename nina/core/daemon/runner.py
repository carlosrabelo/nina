import asyncio
import logging
import os
import signal
from pathlib import Path

import uvicorn

from nina.cli._env import load_project_dotenv
from nina.core.config.required_env import exit_if_missing_required_env
from nina.core.daemon.http import create_app
from nina.core.locale.store import ensure_default as ensure_default_locale
from nina.core.scheduler.runner import Scheduler
from nina.skills.notifications.store import ensure_default as ensure_default_notifications
from nina.skills.presence.store import ensure_default as ensure_default_presence
from nina.skills.profile.store import ensure_default as ensure_default_profile
from nina.skills.workdays.store import ensure_default as ensure_default_workdays


def _init_state(data_dir: Path) -> None:
    """Ensure default state records exist (idempotent)."""
    ensure_default_presence(data_dir)
    ensure_default_workdays(data_dir)
    ensure_default_notifications(data_dir)
    ensure_default_profile(data_dir)
    ensure_default_locale(data_dir)


async def _serve(
    tokens_dir: Path,
    data_dir: Path,
    sessions_dir: Path,
    port: int,
    scheduler: Scheduler,
    dev: bool,
) -> None:
    http_app = create_app(tokens_dir, data_dir)
    host = os.environ.get("NINA_HTTP_HOST", "127.0.0.1")
    config = uvicorn.Config(http_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    loop = asyncio.get_running_loop()

    def _shutdown(sig: int, frame: object) -> None:  # noqa: ARG001
        logging.info("Shutting down Nina daemon...")
        scheduler.stop()
        server.should_exit = True

    loop.add_signal_handler(signal.SIGINT, _shutdown, signal.SIGINT, None)
    loop.add_signal_handler(signal.SIGTERM, _shutdown, signal.SIGTERM, None)

    if not dev:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        owner_raw = os.environ.get("TELEGRAM_OWNER_ID", "")

        if not bot_token or not owner_raw:
            logging.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_OWNER_ID missing — bot disabled")
        else:
            try:
                owner_id = int(owner_raw)
            except ValueError:
                logging.warning("TELEGRAM_OWNER_ID is not a valid integer — bot disabled")
                await server.serve()
                return

            from nina.integrations.telegram.bot import create_application

            bot = create_application(bot_token, owner_id, tokens_dir, data_dir, sessions_dir)
            async with bot:
                await bot.updater.start_polling()
                await bot.start()
                print(
                    f"Nina daemon started — "
                    f"{scheduler.job_count} job(s) registered, "
                    f"HTTP on http://127.0.0.1:{port}, "
                    f"Telegram bot active"
                )
                await server.serve()
                await bot.updater.stop()
                await bot.stop()
            return

    print(
        f"Nina daemon started — "
        f"{scheduler.job_count} job(s) registered, "
        f"HTTP on http://127.0.0.1:{port}"
    )
    await server.serve()


def run(dev: bool = False) -> None:
    load_project_dotenv()
    exit_if_missing_required_env()
    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    sessions_dir = Path(os.environ.get("SESSIONS_DIR", "sessions"))
    port = int(os.environ.get("NINA_HTTP_PORT", "8765"))

    _init_state(data_dir)

    scheduler = Scheduler()

    if not dev:
        _bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        _owner_raw = os.environ.get("TELEGRAM_OWNER_ID", "")
        if _bot_token and _owner_raw:
            try:
                from nina.core.scheduler.jobs.calendar_notifications import make_job

                scheduler.add_job(
                    make_job(tokens_dir, data_dir, _bot_token, int(_owner_raw)),
                    "interval",
                    minutes=5,
                )
            except Exception as e:
                logging.warning("calendar notifications job not registered: %s", e)
            try:
                from nina.core.scheduler.jobs.gmail_label import make_job as make_email_job

                scheduler.add_job(
                    make_email_job(tokens_dir, data_dir),
                    "interval",
                    minutes=10,
                )
            except Exception as e:
                logging.warning("email learning job not registered: %s", e)

    scheduler.start()

    asyncio.run(_serve(tokens_dir, data_dir, sessions_dir, port, scheduler, dev))
    scheduler.stop()
