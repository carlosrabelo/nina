"""Top-level argparse wiring for `nina`."""

import argparse

from nina.cli import (
    auth,
    calendar,
    console,
    daemon,
    email_learning,
    gmail,
    llm,
    make_aliases,
    revoke,
    status,
    telegram,
)
from nina.cli._env import load_project_dotenv


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
        sub_map = getattr(sub, "_name_parser_map", {})  # type: ignore[attr-defined]
        if topic in sub_map:
            sub_map[topic].print_help()
            return

        parser.print_usage()
        print(f"nina: error: unknown command for help: {topic!r}")
        raise SystemExit(2)

    p_help = sub.add_parser("help", help="Show help (optionally for one command)")
    p_help.add_argument("topic", nargs="?", help="Command name (e.g. gmail, email)")
    p_help.set_defaults(func=cmd_help)

    auth.register(sub)
    status.register(sub)
    revoke.register(sub)
    console.register(sub)
    daemon.register(sub)
    make_aliases.register(sub)
    gmail.register(sub)
    email_learning.register(sub)
    calendar.register(sub)
    telegram.register(sub)
    llm.register(sub)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)
