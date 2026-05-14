"""Top-level argparse wiring for `nina`."""

import argparse
import subprocess
import sys
from pathlib import Path

import nina
from nina.cli import (
    calendar,
    console,
    daemon,
    gmail,
    gmail_label,
    google,
    llm,
    telegram,
)
from nina.cli._env import load_project_dotenv


def cmd_typecheck(args: argparse.Namespace) -> None:
    pkg = Path(nina.__file__).resolve().parent
    cmd: list[str] = [sys.executable, "-m", "mypy"]
    cmd.extend(args.paths if args.paths else [str(pkg)])
    raise SystemExit(subprocess.call(cmd))


def main() -> None:
    load_project_dotenv()
    parser = argparse.ArgumentParser(
        prog="nina",
        description="Nina — personal assistant CLI",
        usage="nina <command> [args]",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "See also:\n"
            "  - GUIDE.md / GUIDE-PT.md  (CLI command reference)\n"
            "  - API.md / API-PT.md      (HTTP API)\n"
            "\n"
            "Tip:\n"
            "  nina help <command>\n"
            "  nina <command> --help\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    def cmd_help(args: argparse.Namespace) -> None:
        topic = (args.topic or "").strip()
        if not topic:
            parser.print_help()
            return

        # argparse stores subparsers in a private map; this is stable enough.
        sub_map = getattr(sub, "_name_parser_map", {})
        if topic in sub_map:
            sub_map[topic].print_help()
            return

        parser.print_usage()
        print(f"nina: error: unknown command for help: {topic!r}")
        raise SystemExit(2)

    p_help = sub.add_parser("help", help="Show help (optionally for one command)")
    p_help.add_argument("topic", nargs="?", help="Command name (e.g. google, telegram)")
    p_help.set_defaults(func=cmd_help)

    google.register(sub)
    telegram.register(sub)
    console.register(sub)
    daemon.register(sub)
    gmail.register(sub)
    gmail_label.register(sub)
    calendar.register(sub)
    llm.register(sub)

    p_tc = sub.add_parser("typecheck", help="Run mypy on the nina package")
    p_tc.add_argument(
        "paths",
        nargs="*",
        help="Paths for mypy (default: installed nina package)",
    )
    p_tc.set_defaults(func=cmd_typecheck)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)
