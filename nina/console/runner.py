"""Nina interactive console — talks to the running daemon."""

import cmd
import os
import shlex
from pathlib import Path

from nina.daemon import client
from nina.i18n import t
from nina.locale.store import load as load_locale
from nina.presence.models import PresenceStatus

_PRESENCE_VALUES = [s.value for s in PresenceStatus]


def _tokens_dir() -> Path:
    return Path(os.environ.get("TOKENS_DIR", "tokens"))


def _lang() -> str:
    return load_locale(_tokens_dir()).lang


class NinaConsole(cmd.Cmd):
    prompt = "nina> "

    def __init__(self) -> None:
        super().__init__()
        self.intro = t("console.intro", _lang())

    # ── presence ──────────────────────────────────────────────────────────────

    def do_presence(self, arg: str) -> None:
        lang = _lang()
        parts = shlex.split(arg) if arg.strip() else []
        try:
            if not parts:
                data = client.get("/presence")
                status = data["status"]
                label = t(f"presence.label.{status}", lang)
                since = data["since"][:16].replace("T", " ")
                note = f"  {data['note']}" if data.get("note") else ""
                since_prefix = t("presence.since_prefix", lang)
                print(f"  {status}  —  {label}  ({since_prefix} {since}){note}")
            else:
                status = parts[0]
                note = parts[1] if len(parts) > 1 else ""
                if status not in _PRESENCE_VALUES:
                    valid = ", ".join(_PRESENCE_VALUES)
                    print(f"  {t('presence.invalid', lang, valid=valid)}")
                    return
                data = client.put("/presence", {"status": status, "note": note})
                label = t(f"presence.label.{data['status']}", lang)
                print(f"  {t('presence.set_ok', lang, status=data['status'], label=label)}")
        except ConnectionError as e:
            print(f"  ✗  {e}")

    def help_presence(self) -> None:
        print(t("help.presence", _lang()))

    def complete_presence(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:  # noqa: ARG002
        return [v for v in _PRESENCE_VALUES if v.startswith(text)]

    # ── health ────────────────────────────────────────────────────────────────

    def do_health(self, arg: str) -> None:  # noqa: ARG002
        lang = _lang()
        try:
            data = client.get("/health")
            print(t("console.health.status", lang, value=data["status"]))
            print(t("console.health.uptime", lang, value=data["uptime"]))
        except ConnectionError as e:
            print(f"  ✗  {e}")

    def help_health(self) -> None:
        print(t("help.health", _lang()))

    # ── workdays ──────────────────────────────────────────────────────────────

    def do_workdays(self, arg: str) -> None:  # noqa: ARG002
        lang = _lang()
        try:
            data = client.get("/workdays")
            print(f"  {t('workdays.timezone', lang, tz=data['timezone'])}\n")
            for d in data["days"]:
                if d["active"] and d["start"] and d["end"]:
                    print(f"  {d['name']:<10}  {d['start']} → {d['end']}")
                else:
                    print(f"  {d['name']:<10}  {t('workdays.off', lang)}")
        except ConnectionError as e:
            print(f"  ✗  {e}")

    def help_workdays(self) -> None:
        print(t("help.workdays", _lang()))

    # ── timezone ──────────────────────────────────────────────────────────────

    def do_timezone(self, arg: str) -> None:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        from nina.workdays.store import load as load_workdays, save as save_workdays
        lang = _lang()
        if not arg.strip():
            try:
                data = client.get("/workdays")
                print(f"  {t('workdays.timezone', lang, tz=data['timezone'])}")
            except ConnectionError as e:
                print(f"  ✗  {e}")
            return
        tz_str = arg.strip()
        try:
            ZoneInfo(tz_str)
        except (ZoneInfoNotFoundError, KeyError):
            print(f"  {t('workdays.timezone_invalid', lang, tz=tz_str)}")
            return
        schedule = load_workdays(_tokens_dir())
        schedule.timezone = tz_str
        save_workdays(schedule, _tokens_dir())
        print(f"  {t('workdays.timezone_set', lang, tz=tz_str)}")

    def help_timezone(self) -> None:
        print(t("help.timezone", _lang()))

    # ── context ───────────────────────────────────────────────────────────────

    def do_context(self, arg: str) -> None:  # noqa: ARG002
        lang = _lang()
        try:
            data = client.get("/workdays/context")
            flags = []
            if data["overtime"]:
                flags.append(t("context.flag.overtime", lang))
            if data["weekend_work"]:
                flags.append(t("context.flag.weekend", lang))
            flags_str = f"  [{', '.join(flags)}]" if flags else ""
            work = t("context.in_work_time" if data["is_work_time"] else "context.off_hours", lang)
            print(f"  {data['label']}{flags_str}")
            print(t("console.context.presence", lang, work=work, presence=data["presence"]))
        except ConnectionError as e:
            print(f"  ✗  {e}")

    def help_context(self) -> None:
        print(t("help.context", _lang()))

    # ── lang ──────────────────────────────────────────────────────────────────

    def do_lang(self, arg: str) -> None:
        from nina.locale.models import SUPPORTED, LocaleConfig
        from nina.locale.store import save
        lang = _lang()
        if not arg.strip():
            print(f"  {t('lang.current', lang, code=lang)}")
            return
        new_lang = arg.strip().lower()
        if new_lang not in SUPPORTED:
            supported = " | ".join(sorted(SUPPORTED))
            print(f"  {t('lang.invalid', lang, code=new_lang, supported=supported)}")
            return
        save(LocaleConfig(lang=new_lang), _tokens_dir())
        print(f"  {t('lang.set_ok', new_lang, code=new_lang)}")

    def help_lang(self) -> None:
        print(t("help.lang", _lang()))

    def complete_lang(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:  # noqa: ARG002
        from nina.locale.models import SUPPORTED
        return [v for v in sorted(SUPPORTED) if v.startswith(text)]

    # ── exit ──────────────────────────────────────────────────────────────────

    def do_exit(self, arg: str) -> bool:  # noqa: ARG002
        print(t("console.bye", _lang()))
        return True

    def do_quit(self, arg: str) -> bool:  # noqa: ARG002
        return self.do_exit(arg)

    def do_EOF(self, arg: str) -> bool:  # noqa: ARG002
        print()
        return self.do_exit(arg)

    def help_exit(self) -> None:
        print(t("help.exit", _lang()))

    # ── default ───────────────────────────────────────────────────────────────

    def default(self, line: str) -> None:
        if line.startswith("/"):
            self.onecmd(line[1:])
            return

        # Free text → LLM interpreter (presence or schedule)
        lang = _lang()
        try:
            from nina.llm.client import LLMClient
            llm = LLMClient.from_env()
        except Exception:
            print(f"  {t('llm.unavailable', lang)}")
            return

        from nina.presence.interpreter import interpret as interpret_presence
        from nina.presence.models import PresenceState
        from nina.presence.store import save as save_presence
        from nina.workdays.interpreter import apply as apply_schedule
        from nina.workdays.interpreter import interpret as interpret_schedule
        from nina.workdays.store import load as load_workdays, save as save_workdays

        presence_intent = interpret_presence(line, llm)
        if presence_intent.action == "set_presence" and presence_intent.status is not None:
            save_presence(PresenceState(status=presence_intent.status, note=presence_intent.note), _tokens_dir())
            label = t(f"presence.label.{presence_intent.status.value}", lang)
            print(f"  {t('llm.presence_set', lang, status=presence_intent.status.value, label=label)}")
            return

        schedule_intent = interpret_schedule(line, llm)
        if schedule_intent.action == "update_schedule":
            schedule = load_workdays(_tokens_dir())
            save_workdays(apply_schedule(schedule_intent, schedule), _tokens_dir())
            print(f"  {t('llm.schedule_set', lang)}")
            return

        print(f"  {t('llm.not_understood', lang)}")

    def emptyline(self) -> None:
        pass


def run() -> None:
    NinaConsole().cmdloop()
