"""`nina daemon` — start scheduler + HTTP server."""

import argparse
import logging


def cmd_daemon(args: argparse.Namespace) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s"
    )
    logging.getLogger("google.oauth2").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)
    from nina.core.daemon.runner import run
    run(dev=args.dev)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("daemon", help="Start Nina in daemon mode (scheduler + HTTP)")
    p.add_argument(
        "--dev", action="store_true", help="Development mode — disables Telegram bot"
    )
    p.set_defaults(func=cmd_daemon)
