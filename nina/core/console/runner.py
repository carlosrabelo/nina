"""Nina interactive console — talks to the running daemon."""

import cmd
import shlex

from nina.core.config.required_env import exit_if_missing_required_env
from nina.core.console.freeform_dispatch import dispatch_natural_language_line
from nina.core.console.paths import console_lang, data_dir, tokens_dir
from nina.core.daemon import client
from nina.core.i18n import t
from nina.skills.presence.models import PresenceStatus

_PRESENCE_VALUES = [s.value for s in PresenceStatus]


class NinaConsole(cmd.Cmd):
    prompt = "nina> "

    def __init__(self) -> None:
        super().__init__()
        self.intro = t("console.intro", console_lang())

    # ── presence ──────────────────────────────────────────────────────────────

    def do_presence(self, arg: str) -> None:
        lang = console_lang()
        parts = shlex.split(arg) if arg.strip() else []
        try:
            if not parts:
                data = client.get("/presence")
                status = data["status"]
                label = t(f"presence.label.{status}", lang)
                from datetime import datetime as _dt
                from zoneinfo import ZoneInfo as _ZI

                from nina.skills.workdays.store import load as _load_wd
                _tz = _ZI(_load_wd(data_dir()).timezone)
                _since_utc = _dt.fromisoformat(data["since"])
                _since_local = _since_utc.astimezone(_tz)
                since = _since_local.strftime("%Y-%m-%d %H:%M")
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
        print(t("help.presence", console_lang()))

    def complete_presence(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:  # noqa: ARG002
        return [v for v in _PRESENCE_VALUES if v.startswith(text)]

    # ── health ────────────────────────────────────────────────────────────────

    def do_health(self, arg: str) -> None:  # noqa: ARG002
        lang = console_lang()
        try:
            data = client.get("/health")
            print(t("console.health.status", lang, value=data["status"]))
            print(t("console.health.uptime", lang, value=data["uptime"]))
        except ConnectionError as e:
            print(f"  ✗  {e}")

    def help_health(self) -> None:
        print(t("help.health", console_lang()))

    # ── workdays ──────────────────────────────────────────────────────────────

    def do_workdays(self, arg: str) -> None:  # noqa: ARG002
        lang = console_lang()
        try:
            data = client.get("/workdays")
            print(f"  {t('workdays.timezone', lang, tz=data['timezone'])}\n")
            for d in data["days"]:
                if d["active"] and d["start"] and d["end"]:
                    lunch = ""
                    if d.get("lunch_start") and d.get("lunch_end"):
                        lunch = f"  ({t('workdays.lunch', lang, start=d['lunch_start'], end=d['lunch_end'])})"
                    print(f"  {d['name']:<10}  {d['start']} → {d['end']}{lunch}")
                else:
                    print(f"  {d['name']:<10}  {t('workdays.off', lang)}")
        except ConnectionError as e:
            print(f"  ✗  {e}")

    def help_workdays(self) -> None:
        print(t("help.workdays", console_lang()))

    # ── timezone ──────────────────────────────────────────────────────────────

    def do_timezone(self, arg: str) -> None:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        from nina.skills.workdays.store import load as load_workdays
        from nina.skills.workdays.store import save as save_workdays
        lang = console_lang()
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
        schedule = load_workdays(data_dir())
        schedule.timezone = tz_str
        save_workdays(schedule, data_dir())
        print(f"  {t('workdays.timezone_set', lang, tz=tz_str)}")

    def help_timezone(self) -> None:
        print(t("help.timezone", console_lang()))

    # ── context ───────────────────────────────────────────────────────────────

    def do_context(self, arg: str) -> None:  # noqa: ARG002
        lang = console_lang()
        try:
            data = client.get("/workdays/context")
            flags = []
            if data["overtime"]:
                flags.append(t("context.flag.overtime", lang))
            if data["weekend_work"]:
                flags.append(t("context.flag.weekend", lang))
            flags_str = f"  [{', '.join(flags)}]" if flags else ""
            if data["is_work_time"]:
                work = t("context.in_work_time", lang)
            elif data.get("is_lunch_time"):
                work = t("context.lunch_time", lang)
            else:
                work = t("context.off_hours", lang)
            print(f"  {data['label']}{flags_str}")
            print(t("console.context.presence", lang, work=work, presence=data["presence"]))
        except ConnectionError as e:
            print(f"  ✗  {e}")

    def help_context(self) -> None:
        print(t("help.context", console_lang()))

    # ── profile ───────────────────────────────────────────────────────────────

    def do_profile(self, arg: str) -> None:
        from nina.skills.presence.models import PresenceStatus
        from nina.skills.profile.store import load as load_profile
        lang = console_lang()
        profile = load_profile(data_dir())

        statuses = list(PresenceStatus)
        if arg.strip():
            try:
                statuses = [PresenceStatus(arg.strip().lower())]
            except ValueError:
                pass

        if profile.is_empty():
            print(f"  {t('profile.empty', lang)}")
            return

        print(f"  {t('profile.title', lang)}")
        for status in statuses:
            p = profile.for_presence(status)
            label = t(f"presence.label.{status.value}", lang)
            print(f"\n  {status.value} — {label}")
            if p.gmail:
                print(f"    {t('profile.gmail', lang, accounts=', '.join(p.gmail))}")
            if p.calendar:
                print(f"    {t('profile.calendar', lang, accounts=', '.join(p.calendar))}")
            if not p.gmail and not p.calendar:
                print(f"    {t('profile.no_accounts', lang)}")

    def help_profile(self) -> None:
        print(t("help.profile", console_lang()))

    def complete_profile(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:  # noqa: ARG002
        return [v for v in _PRESENCE_VALUES if v.startswith(text)]

    # ── lang ──────────────────────────────────────────────────────────────────

    def do_lang(self, arg: str) -> None:
        from nina.core.locale.models import SUPPORTED, LocaleConfig
        from nina.core.locale.store import save
        lang = console_lang()
        if not arg.strip():
            print(f"  {t('lang.current', lang, code=lang)}")
            return
        new_lang = arg.strip().lower()
        if new_lang not in SUPPORTED:
            supported = " | ".join(sorted(SUPPORTED))
            print(f"  {t('lang.invalid', lang, code=new_lang, supported=supported)}")
            return
        save(LocaleConfig(lang=new_lang), data_dir())
        print(f"  {t('lang.set_ok', new_lang, code=new_lang)}")

    def help_lang(self) -> None:
        print(t("help.lang", console_lang()))

    def complete_lang(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:  # noqa: ARG002
        from nina.core.locale.models import SUPPORTED
        return [v for v in sorted(SUPPORTED) if v.startswith(text)]

    # ── notify ────────────────────────────────────────────────────────────────

    def do_notify(self, arg: str) -> None:
        lang = console_lang()
        parts = arg.strip().split()
        try:
            if not parts:
                data = client.get("/notifications/config")
                print(f"  {t('notify.config', lang, reminder_minutes=data['reminder_minutes'], watch_days=data['watch_days'])}")
            elif parts[0] == "reminder" and len(parts) == 2:
                val = int(parts[1])
                if val <= 0:
                    raise ValueError
                client.put("/notifications/config", {"reminder_minutes": val})
                print(f"  {t('notify.reminder_set', lang, minutes=val)}")
            elif parts[0] == "days" and len(parts) == 2:
                val = int(parts[1])
                if val <= 0:
                    raise ValueError
                client.put("/notifications/config", {"watch_days": val})
                print(f"  {t('notify.days_set', lang, days=val)}")
            else:
                print(f"  {t('notify.usage', lang)}")
        except ValueError:
            raw = parts[1] if len(parts) > 1 else ""
            print(f"  {t('notify.invalid_value', lang, value=raw)}")
        except ConnectionError as e:
            print(f"  ✗  {e}")

    def help_notify(self) -> None:
        print(t("help.notify", console_lang()))

    # ── schedule ──────────────────────────────────────────────────────────────

    def do_schedule(self, arg: str) -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from nina.skills.calendar.schedule_parser import parse as parse_schedule
        from nina.skills.workdays.store import load as load_workdays
        lang = console_lang()
        if not arg.strip():
            print(t("schedule.parse_error", lang))
            return
        schedule = load_workdays(data_dir())
        tz = ZoneInfo(schedule.timezone)
        now = datetime.now(tz)
        parsed = parse_schedule(arg, now)
        if parsed is None:
            print(f"  {t('schedule.parse_error', lang)}")
            return
        try:
            data = client.post("/schedule", {
                "start_time": parsed.start.strftime("%H:%M"),
                "title": parsed.title,
                "duration_minutes": parsed.duration_minutes,
            })
        except ConnectionError as e:
            print(f"  ✗  {e}")
            return
        if "detail" in data:
            if data["detail"] == "no_calendar_account":
                print(f"  {t('schedule.no_account', lang)}")
            else:
                print(f"  ✗  {data['detail']}")
            return
        _WEEKDAY_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
        _WEEKDAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        from datetime import datetime as _dt
        _start_dt = _dt.fromisoformat(data["start"])
        _wd = _start_dt.weekday()
        _day_abbr = (_WEEKDAY_PT[_wd] if lang == "pt" else _WEEKDAY_EN[_wd])
        date_label = f"{_day_abbr}, {_start_dt.strftime('%d/%m')}"
        start = data["start"][11:16]
        end = data["end"][11:16]
        print(f"  {t('schedule.created', lang, title=data['event_title'], date=date_label, start=start, end=end, account=data['account'])}")
        if data.get("conflicts"):
            print(f"  {t('schedule.conflict', lang, titles=', '.join(data['conflicts']))}")

    def help_schedule(self) -> None:
        print(t("help.schedule", console_lang()))

    # ── memo / memos ──────────────────────────────────────────────────────────

    def do_memo(self, arg: str) -> None:
        from nina.core.store.db import open_db
        from nina.core.store.models import Memo
        from nina.core.store.repos import memo as memo_repo
        lang = console_lang()
        parts = arg.strip().split()

        if not parts:
            print(f"  {t('memo.usage', lang)}")
            return

        conn = open_db(data_dir())

        # memo done <id_prefix>
        if parts[0] == "done":
            if len(parts) < 2:
                print(f"  {t('memo.usage', lang)}")
                return
            prefix = parts[1]
            memos = [m for m in memo_repo.list_all(conn) if m.id.startswith(prefix)]
            if not memos:
                print(f"  {t('memo.not_found', lang)}")
                return
            memo_repo.done(conn, memos[0].id)
            print(f"  {t('memo.done', lang)}")
            return

        # memo dismiss <id_prefix>
        if parts[0] == "dismiss":
            if len(parts) < 2:
                print(f"  {t('memo.usage', lang)}")
                return
            prefix = parts[1]
            memos = [m for m in memo_repo.list_all(conn) if m.id.startswith(prefix)]
            if not memos:
                print(f"  {t('memo.not_found', lang)}")
                return
            memo_repo.dismiss(conn, memos[0].id)
            print(f"  {t('memo.dismissed', lang)}")
            return

        # memo <text> [due <date>]
        text_parts = arg.strip().split(" due ", 1)
        text = text_parts[0].strip()
        due_date = text_parts[1].strip() if len(text_parts) > 1 else None
        memo_repo.add(conn, Memo(text=text, due_date=due_date))
        print(f"  {t('memo.saved', lang)}")

    def do_memos(self, arg: str) -> None:  # noqa: ARG002
        from nina.core.store.db import open_db
        from nina.core.store.repos import memo as memo_repo
        lang = console_lang()
        conn = open_db(data_dir())
        memos = memo_repo.list_open(conn)
        if not memos:
            print(f"  {t('memo.none_open', lang)}")
            return
        for i, m in enumerate(memos, 1):
            due = t("memo.due", lang, date=m.due_date) if m.due_date else ""
            short_id = m.id[:8]
            print(f"  [{short_id}] {m.text}{due}")

    def help_memo(self) -> None:
        print(t("help.memo", console_lang()))

    def help_memos(self) -> None:
        print(t("help.memo", console_lang()))

    # ── gmail_label (Telegram parity; same behaviour as /gmail_label on the bot) ─────

    def do_gmail_label(self, arg: str) -> None:
        from nina.skills.gmail_label.execute import (
            add_ignored,
            add_rule_direct,
            check_rules,
            dismiss_all_pending_labels,
            dismiss_pending_by_prefix,
            format_ignored_list,
            format_pending_list,
            remove_ignored,
            teach_label_for_pending,
        )

        lang = console_lang()
        dd = data_dir()
        td = tokens_dir()
        parts = shlex.split(arg) if arg.strip() else []

        if not parts:
            text = format_pending_list(dd)
            for part in text.split("\n"):
                print(f"  {part}")
            return
        if parts[0].lower() == "dismiss":
            if len(parts) < 2:
                print(f"  {t('gmail_label.usage', lang)}")
                return
            out = dismiss_pending_by_prefix(dd, parts[1])
            print(f"  {out}")
            return
        if parts[0].lower() == "dismiss-all":
            out = dismiss_all_pending_labels(dd)
            print(f"  {out}")
            return
        if parts[0].lower() == "rule":
            if len(parts) < 4 or parts[1].lower() != "add":
                print(f"  {t('gmail_label.usage', lang)}")
                return
            out = add_rule_direct(dd, parts[2], parts[3], " ".join(parts[4:]))
            print(f"  {out}")
            return
        if parts[0].lower() == "rules":
            if len(parts) < 2 or parts[1].lower() != "check":
                print(f"  {t('gmail_label.usage', lang)}")
                return
            out = check_rules(dd, td)
            for part in out.split("\n"):
                print(f"  {part}")
            return
        if parts[0].lower() == "ignore":
            if len(parts) < 2 or parts[1].lower() not in ("list", "add", "remove"):
                print(f"  {t('gmail_label.ignore_usage', lang)}")
                return
            sub = parts[1].lower()
            if sub == "list":
                acct = parts[2] if len(parts) > 2 else None
                text = format_ignored_list(dd, account=acct)
                for part in text.split("\n"):
                    print(f"  {part}")
                return
            if sub == "add":
                if len(parts) < 4:
                    print(f"  {t('gmail_label.ignore_usage', lang)}")
                    return
                out = add_ignored(dd, parts[2], parts[3])
                print(f"  {out}")
                return
            if sub == "remove":
                if len(parts) < 4:
                    print(f"  {t('gmail_label.ignore_usage', lang)}")
                    return
                out = remove_ignored(dd, parts[2], parts[3])
                print(f"  {out}")
                return
        if len(parts) < 2:
            print(f"  {t('gmail_label.usage', lang)}")
            return
        pending_prefix = parts[0]
        label = " ".join(parts[1:])
        out = teach_label_for_pending(td, dd, pending_prefix, label)
        print(f"  {out}")

    def help_gmail_label(self) -> None:
        print(t("help.gmail_label", console_lang()))

    # ── exit ──────────────────────────────────────────────────────────────────

    def do_exit(self, arg: str) -> bool:  # noqa: ARG002
        print(t("console.bye", console_lang()))
        return True

    def do_quit(self, arg: str) -> bool:  # noqa: ARG002
        return self.do_exit(arg)

    def do_EOF(self, arg: str) -> bool:  # noqa: ARG002
        print()
        return self.do_exit(arg)

    def help_exit(self) -> None:
        print(t("help.exit", console_lang()))

    # ── default ───────────────────────────────────────────────────────────────

    def default(self, line: str) -> None:
        if line.startswith("/"):
            self.onecmd(line[1:])
            return

        stripped = line.strip()
        if stripped.startswith("gmail_label"):
            parts = shlex.split(stripped)
            if parts and parts[0] == "gmail_label":
                self.do_gmail_label(" ".join(parts[1:]))
                return

        dispatch_natural_language_line(line)

    def emptyline(self) -> None:
        pass


def run() -> None:
    exit_if_missing_required_env()
    NinaConsole().cmdloop()
