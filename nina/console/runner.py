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


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data"))


def _lang() -> str:
    return load_locale(_data_dir()).lang


def _execute_calendar_intent(action: str, lang: str) -> None:
    from nina.errors import CalendarError
    from nina.google.calendar.client import CalendarClient
    from nina.presence.store import load as load_presence
    from nina.profile.store import load as load_profile
    if action == "list":
        presence = load_presence(_data_dir())
        profile = load_profile(_data_dir())
        cal_accounts = profile.for_presence(presence.status).calendar
        if not cal_accounts:
            print(f"  {t('blocking.no_account', lang)}")
            return
        try:
            client = CalendarClient(cal_accounts[0], _tokens_dir())
            events = client.list_upcoming(max_results=10)
        except CalendarError as e:
            print(f"  ✗  {e}")
            return
        if not events:
            print(f"  {t('calendar.no_events', lang)}")
            return
        for ev in events:
            start = ev.start.strftime("%d/%m %H:%M")
            print(f"  {start}  {ev.title}")


def _execute_obsidian_intent(lang: str) -> None:
    from nina.obsidian import vault_path
    if vault_path() is None:
        print(f"  {t('obsidian.not_set', lang)}")
        return
    from nina.scheduler.jobs.obsidian_sync import make_job
    make_job(_tokens_dir(), _data_dir())()
    print(f"  {t('obsidian.done', lang, path=str(vault_path()))}")


def _execute_notification_intent(action: str, minutes: int | None, days: int | None, lang: str) -> None:
    from nina.notifications.models import NotificationConfig
    from nina.notifications.store import load as load_notif, save as save_notif
    state = load_notif(_data_dir())
    if action == "get":
        print(f"  {t('notify.config', lang, reminder_minutes=state.config.reminder_minutes, watch_days=state.config.watch_days)}")
        return
    if action == "set_reminder" and minutes is not None:
        state.config.reminder_minutes = minutes
        save_notif(state, _data_dir())
        print(f"  {t('notify.reminder_set', lang, minutes=minutes)}")
        return
    if action == "set_days" and days is not None:
        state.config.watch_days = days
        save_notif(state, _data_dir())
        print(f"  {t('notify.days_set', lang, days=days)}")
        return
    print(f"  {t('notify.usage', lang)}")


def _execute_memo_intent(action: str, subject: str, lang: str, due_date: str = "") -> None:
    from nina.store.db import open_db
    from nina.store.models import Memo
    from nina.store.repos import memo as memo_repo
    conn = open_db(_data_dir())
    if action == "list":
        memos = memo_repo.list_open(conn)
        if not memos:
            print(f"  {t('memo.none_open', lang)}")
            return
        for m in memos:
            due = t("memo.due", lang, date=m.due_date) if m.due_date else ""
            print(f"  [{m.id[:8]}] {m.text}{due}")
        return
    if action == "remind":
        memo_repo.add(conn, Memo(text=subject, due_date=due_date or None))
        if due_date:
            print(f"  {t('memo.remind_set', lang, date=due_date, subject=subject)}")
        else:
            print(f"  {t('memo.saved', lang)}")
        return
    matches = [m for m in memo_repo.list_open(conn) if subject.lower() in m.text.lower()]
    if not matches:
        print(f"  {t('memo.not_found', lang)}")
        return
    for m in matches:
        if action == "close":
            memo_repo.done(conn, m.id)
            print(f"  {t('memo.done', lang)} — {m.text}")
        elif action == "dismiss":
            memo_repo.dismiss(conn, m.id)
            print(f"  {t('memo.dismissed', lang)} — {m.text}")


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
        schedule = load_workdays(_data_dir())
        schedule.timezone = tz_str
        save_workdays(schedule, _data_dir())
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

    # ── profile ───────────────────────────────────────────────────────────────

    def do_profile(self, arg: str) -> None:
        from nina.presence.models import PresenceStatus
        from nina.profile.store import load as load_profile
        lang = _lang()
        profile = load_profile(_data_dir())

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
        print(t("help.profile", _lang()))

    def complete_profile(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:  # noqa: ARG002
        return [v for v in _PRESENCE_VALUES if v.startswith(text)]

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
        save(LocaleConfig(lang=new_lang), _data_dir())
        print(f"  {t('lang.set_ok', new_lang, code=new_lang)}")

    def help_lang(self) -> None:
        print(t("help.lang", _lang()))

    def complete_lang(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:  # noqa: ARG002
        from nina.locale.models import SUPPORTED
        return [v for v in sorted(SUPPORTED) if v.startswith(text)]

    # ── notify ────────────────────────────────────────────────────────────────

    def do_notify(self, arg: str) -> None:
        lang = _lang()
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
        print(t("help.notify", _lang()))

    # ── schedule ──────────────────────────────────────────────────────────────

    def do_schedule(self, arg: str) -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from nina.google.calendar.schedule_parser import parse as parse_schedule
        from nina.workdays.store import load as load_workdays
        lang = _lang()
        if not arg.strip():
            print(t("schedule.parse_error", lang))
            return
        schedule = load_workdays(_data_dir())
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
        start = data["start"][11:16]
        end = data["end"][11:16]
        print(f"  {t('schedule.created', lang, title=data['event_title'], start=start, end=end, account=data['account'])}")
        if data.get("link"):
            print(f"  {data['link']}")
        if data.get("conflicts"):
            print(f"  {t('schedule.conflict', lang, titles=', '.join(data['conflicts']))}")

    def help_schedule(self) -> None:
        print(t("help.schedule", _lang()))

    # ── memo / memos ──────────────────────────────────────────────────────────

    def do_memo(self, arg: str) -> None:
        from nina.store.db import open_db
        from nina.store.models import Memo
        from nina.store.repos import memo as memo_repo
        lang = _lang()
        parts = arg.strip().split()

        if not parts:
            print(f"  {t('memo.usage', lang)}")
            return

        conn = open_db(_data_dir())

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
        from nina.store.db import open_db
        from nina.store.repos import memo as memo_repo
        lang = _lang()
        conn = open_db(_data_dir())
        memos = memo_repo.list_open(conn)
        if not memos:
            print(f"  {t('memo.none_open', lang)}")
            return
        for i, m in enumerate(memos, 1):
            due = t("memo.due", lang, date=m.due_date) if m.due_date else ""
            short_id = m.id[:8]
            print(f"  [{short_id}] {m.text}{due}")

    def help_memo(self) -> None:
        print(t("help.memo", _lang()))

    def help_memos(self) -> None:
        print(t("help.memo", _lang()))

    # ── obsidian ──────────────────────────────────────────────────────────────

    def do_obsidian(self, arg: str) -> None:  # noqa: ARG002
        from nina.obsidian import vault_path
        lang = _lang()
        if vault_path() is None:
            print(f"  {t('obsidian.not_set', lang)}")
            return
        from nina.scheduler.jobs.obsidian_sync import make_job
        make_job(_tokens_dir(), _data_dir())()
        print(f"  {t('obsidian.done', lang, path=str(vault_path()))}")

    def help_obsidian(self) -> None:
        print(t("help.obsidian", _lang()))

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

        lang = _lang()

        # Layer 1 — pattern match, zero LLM calls
        from nina.memo.interpreter import try_action as memo_try
        result = memo_try(line, lang)
        if result:
            _execute_memo_intent(result.action, result.subject, lang)
            return

        from nina.google.calendar.interpreter import try_action as cal_try
        cal_result = cal_try(line, lang)
        if cal_result:
            _execute_calendar_intent(cal_result.action, lang)
            return

        from nina.obsidian.interpreter import try_action as obsidian_try
        if obsidian_try(line, lang):
            _execute_obsidian_intent(lang)
            return

        from nina.notifications.interpreter import try_action as notif_try
        notif_result = notif_try(line, lang)
        if notif_result:
            _execute_notification_intent(notif_result.action, notif_result.minutes, notif_result.days, lang)
            return

        # Keyword gates — determine candidates without calling LLM
        from nina.google.calendar.blocking import has_time_signal
        from nina.google.calendar.interpreter import has_context as cal_has
        from nina.notifications.interpreter import has_context as notif_has
        from nina.obsidian.interpreter import has_context as obsidian_has
        from nina.presence.interpreter import has_context as presence_has
        from nina.profile.interpreter import has_context as profile_has
        from nina.workdays.interpreter import has_context as schedule_has

        from nina.memo.interpreter import has_reminder_context
        candidates: set[str] = set()
        if "memo" in line.lower() or has_reminder_context(line, lang):
            candidates.add("memo")
        if cal_has(line, lang):
            candidates.add("calendar")
        if has_time_signal(line):
            candidates.add("blocking")
        if presence_has(line, lang):
            candidates.add("presence")
        if schedule_has(line, lang):
            candidates.add("schedule")
        if profile_has(line, lang):
            candidates.add("profile")
        if obsidian_has(line, lang):
            candidates.add("obsidian")
        if notif_has(line, lang):
            candidates.add("notifications")

        # Load LLM once
        try:
            from nina.llm.client import LLMClient
            llm = LLMClient.from_env()
        except Exception:
            print(f"  {t('llm.unavailable', lang)}")
            return

        # If no keyword gate fired, ask router LLM to classify
        if not candidates:
            from nina.intent.router import route
            domain = route(line, llm).domain
            if domain == "none":
                print(f"  {t('llm.not_understood', lang)}")
                return
            candidates = {domain}

        # Execute candidates in priority order
        from nina.errors import CalendarError
        from nina.google.calendar.blocking import execute as execute_blocking
        from nina.google.calendar.blocking import interpret as interpret_blocking
        from nina.presence.interpreter import interpret as interpret_presence
        from nina.presence.models import PresenceState
        from nina.presence.store import load as load_presence, save as save_presence
        from nina.profile.interpreter import apply as apply_profile
        from nina.profile.interpreter import interpret as interpret_profile
        from nina.profile.store import load as load_profile, save as save_profile
        from nina.workdays.interpreter import apply as apply_schedule
        from nina.workdays.interpreter import interpret as interpret_schedule
        from nina.workdays.store import load as load_workdays, save as save_workdays
        from datetime import datetime
        from zoneinfo import ZoneInfo

        if "memo" in candidates:
            from nina.memo.interpreter import interpret as memo_interpret
            _now = datetime.now(ZoneInfo(load_workdays(_data_dir()).timezone))
            memo_intent = memo_interpret(line, llm, lang=lang, now=_now)
            if memo_intent.action != "none":
                _execute_memo_intent(memo_intent.action, memo_intent.subject, lang, memo_intent.due_date)
                return

        if "calendar" in candidates:
            from nina.google.calendar.interpreter import interpret as cal_interpret
            cal_intent = cal_interpret(line, llm, lang)
            if cal_intent.action != "none":
                _execute_calendar_intent(cal_intent.action, lang)
                return

        if "blocking" in candidates:
            _schedule_pre = load_workdays(_data_dir())
            _now = datetime.now(ZoneInfo(_schedule_pre.timezone))
            blocking_intents = interpret_blocking(line, llm, now=_now)
            if blocking_intents:
                presence = load_presence(_data_dir())
                profile = load_profile(_data_dir())
                cal_accounts = profile.best_calendar_accounts(line, presence.status)
                if not cal_accounts:
                    print(f"  {t('blocking.no_account', lang)}")
                    return
                time_fmt = "%H:%M"
                for blocking_intent in blocking_intents:
                    try:
                        result = execute_blocking(
                            blocking_intent,
                            account=cal_accounts[0],
                            tokens_dir=_tokens_dir(),
                            tz_name=_schedule_pre.timezone,
                        )
                    except CalendarError as e:
                        print(f"  ✗  {e}")
                        continue
                    print(f"  {t('blocking.created', lang, title=result.event_title, start=result.start.strftime(time_fmt), end=result.end.strftime(time_fmt), account=cal_accounts[0])}")
                    if result.link:
                        print(f"  {result.link}")
                    if result.conflicts:
                        print(f"  {t('blocking.conflict', lang, titles=', '.join(result.conflicts))}")
                return

        if "presence" in candidates:
            presence_intent = interpret_presence(line, llm)
            if presence_intent.action == "set_presence" and presence_intent.status is not None:
                save_presence(PresenceState(status=presence_intent.status, note=presence_intent.note), _data_dir())
                label = t(f"presence.label.{presence_intent.status.value}", lang)
                print(f"  {t('llm.presence_set', lang, status=presence_intent.status.value, label=label)}")
                return

        if "schedule" in candidates:
            schedule_intent = interpret_schedule(line, llm)
            if schedule_intent.action == "update_schedule":
                schedule = load_workdays(_data_dir())
                save_workdays(apply_schedule(schedule_intent, schedule), _data_dir())
                print(f"  {t('llm.schedule_set', lang)}")
                return

        if "profile" in candidates:
            profile_intent = interpret_profile(line, llm)
            if profile_intent.action == "update_profile":
                profile = load_profile(_data_dir())
                save_profile(apply_profile(profile_intent, profile), _data_dir())
                print(f"  {t('profile.set_ok', lang)}")
                return

        if "obsidian" in candidates:
            _execute_obsidian_intent(lang)
            return

        if "notifications" in candidates:
            from nina.notifications.interpreter import interpret as notif_interpret
            notif_intent = notif_interpret(line, llm)
            if notif_intent.action != "none":
                _execute_notification_intent(notif_intent.action, notif_intent.minutes, notif_intent.days, lang)
                return

        print(f"  {t('llm.not_understood', lang)}")

    def emptyline(self) -> None:
        pass


def run() -> None:
    NinaConsole().cmdloop()
