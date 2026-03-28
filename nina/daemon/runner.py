import asyncio
import logging
import os
import signal
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from nina.daemon.http import create_app
from nina.presence.store import load as load_presence, save as save_presence
from nina.workdays.store import load as load_schedule, save as save_schedule
from nina.scheduler.runner import Scheduler


def _init_state(tokens_dir: Path) -> None:
    """Persist default state files on first run."""
    save_presence(load_presence(tokens_dir), tokens_dir)
    save_schedule(load_schedule(tokens_dir), tokens_dir)


async def _serve(tokens_dir: Path, port: int, scheduler: Scheduler) -> None:
    http_app = create_app(tokens_dir)
    config = uvicorn.Config(http_app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    owner_raw = os.environ.get("TELEGRAM_OWNER_ID", "")

    loop = asyncio.get_running_loop()

    def _shutdown(sig: int, frame: object) -> None:  # noqa: ARG001
        logging.info("Shutting down Nina daemon...")
        scheduler.stop()
        server.should_exit = True

    loop.add_signal_handler(signal.SIGINT, _shutdown, signal.SIGINT, None)
    loop.add_signal_handler(signal.SIGTERM, _shutdown, signal.SIGTERM, None)

    if bot_token and owner_raw:
        try:
            owner_id = int(owner_raw)
        except ValueError:
            logging.warning("TELEGRAM_OWNER_ID is not a valid integer — bot disabled")
            await server.serve()
            return

        from nina.telegram.bot import create_application
        bot = create_application(bot_token, owner_id, tokens_dir)
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
    else:
        print(
            f"Nina daemon started — "
            f"{scheduler.job_count} job(s) registered, "
            f"HTTP on http://127.0.0.1:{port}"
        )
        await server.serve()


def run() -> None:
    load_dotenv()
    tokens_dir = Path(os.environ.get("TOKENS_DIR", "tokens"))
    port = int(os.environ.get("NINA_HTTP_PORT", "8765"))

    _init_state(tokens_dir)

    scheduler = Scheduler()
    # Jobs will be registered here as they are implemented.
    scheduler.start()

    asyncio.run(_serve(tokens_dir, port, scheduler))
    scheduler.stop()
