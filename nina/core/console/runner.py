"""Nina interactive console — talks to the running daemon."""

import cmd
import os
import shlex
from pathlib import Path

from nina.core.daemon import client
from nina.core.i18n import t
from nina.core.locale.store import load as load_locale
from nina.skills.presence.models import PresenceStatus

_PRESENCE_VALUES = [s.value for s in PresenceStatus]


def _tokens_dir() -> Path:
    return Path(os.environ.get("TOKENS_DIR", "tokens"))


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data"))


def _lang() -> str:
    return load_locale(_data_dir()).lang


def _execute_calendar_intent(action: str, lang: str) -> None:
    from nina.errors import CalendarError
    from nina.integrations.google.calendar.client import CalendarClient
    from nina.skills.presence.store import load as load_presence
    from nina.skills.profile.store import load as load_profile
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


def _execute_notification_intent(action: str, minutes: int | None, days: int | None, lang: str) -> None:
    from nina.skills.notifications.models import NotificationConfig
    from nina.skills.notifications.store import load as load_notif, save as save_notif
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
    from nina.core.store.db import open_db
    from nina.core.store.models import Memo
    from nina.core.store.repos import memo as memo_repo
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
                from datetime import datetime as _dt
                from zoneinfo import ZoneInfo as _ZI
                from nina.skills.workdays.store import load as _load_wd
                _tz = _ZI(_load_wd(_data_dir()).timezone)
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
        from nina.skills.workdays.store import load as load_workdays, save as save_workdays
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
        from nina.skills.presence.models import PresenceStatus
        from nina.skills.profile.store import load as load_profile
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
        from nina.core.locale.models import SUPPORTED, LocaleConfig
        from nina.core.locale.store import save
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
        from nina.core.locale.models import SUPPORTED
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
        from nina.skills.calendar.schedule_parser import parse as parse_schedule
        from nina.skills.workdays.store import load as load_workdays
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
        print(t("help.schedule", _lang()))

    # ── memo / memos ──────────────────────────────────────────────────────────

    def do_memo(self, arg: str) -> None:
        from nina.core.store.db import open_db
        from nina.core.store.models import Memo
        from nina.core.store.repos import memo as memo_repo
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
        from nina.core.store.db import open_db
        from nina.core.store.repos import memo as memo_repo
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
        from nina.skills.memo.interpreter import try_action as memo_try
        result = memo_try(line, lang)
        if result:
            _execute_memo_intent(result.action, result.subject, lang)
            return

        from nina.skills.calendar.interpreter import try_action as cal_try
        if cal_result := cal_try(line, lang):
            _execute_calendar_intent(cal_result.action, lang)
            return

        from nina.skills.notifications.interpreter import try_action as notif_try
        if notif_result := notif_try(line, lang):
            _execute_notification_intent(notif_result.action, notif_result.minutes, notif_result.days, lang)
            return

        # Layer 2 — unified router: 1 LLM call classifies domain AND extracts entities
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from nina.skills.workdays.store import load as load_workdays

        try:
            from nina.core.llm.client import LLMClient
            llm = LLMClient.from_env()
        except Exception:
            print(f"  {t('llm.unavailable', lang)}")
            return

        _schedule = load_workdays(_data_dir())
        _now = datetime.now(ZoneInfo(_schedule.timezone))

        from nina.core.intent.router import route
        intent = route(line, llm, lang=lang, now=_now)

        if intent.domain == "none":
            print(f"  {t('llm.not_understood', lang)}")
            return

        # Simple domains — executed directly from router output (no extra LLM call)
        if intent.domain == "presence" and intent.status:
            from nina.skills.presence.models import PresenceState, PresenceStatus
            from nina.skills.presence.store import save as save_presence
            try:
                status = PresenceStatus(intent.status)
            except ValueError:
                print(f"  {t('llm.not_understood', lang)}")
                return
            save_presence(PresenceState(status=status, note=intent.note), _data_dir())
            label = t(f"presence.label.{status.value}", lang)
            print(f"  {t('llm.presence_set', lang, status=status.value, label=label)}")
            return

        if intent.domain == "memo" and intent.action != "none":
            _execute_memo_intent(intent.action, intent.subject, lang, intent.due_date)
            return

        if intent.domain == "calendar":
            _execute_calendar_intent(intent.action, lang)
            return

        if intent.domain == "notifications" and intent.action != "none":
            _execute_notification_intent(intent.action, intent.minutes, intent.days, lang)
            return

        if intent.domain == "profile" and intent.updates:
            from nina.skills.profile.interpreter import ProfileIntent, ProfileUpdate, apply as apply_profile
            from nina.skills.profile.store import load as load_profile, save as save_profile
            updates = [
                ProfileUpdate(
                    presence=u["presence"],
                    gmail=list(u.get("gmail", [])),
                    calendar=list(u.get("calendar", [])),
                )
                for u in intent.updates
                if u.get("presence")
            ]
            if updates:
                profile = load_profile(_data_dir())
                save_profile(apply_profile(ProfileIntent(action="update_profile", updates=updates), profile), _data_dir())
                print(f"  {t('profile.set_ok', lang)}")
                return

        # Complex domains — need a second dedicated LLM call
        if intent.domain == "blocking":
            from nina.errors import CalendarError
            from nina.skills.calendar.blocking import execute as execute_blocking
            from nina.skills.calendar.blocking import interpret as interpret_blocking
            from nina.skills.presence.store import load as load_presence
            from nina.skills.profile.store import load as load_profile
            blocking_intents = interpret_blocking(line, llm, now=_now)
            if blocking_intents:
                presence = load_presence(_data_dir())
                profile = load_profile(_data_dir())
                cal_accounts = profile.best_calendar_accounts(line, presence.status)
                if not cal_accounts:
                    print(f"  {t('blocking.no_account', lang)}")
                    return
                _WEEKDAY_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
                _WEEKDAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                time_fmt = "%H:%M"
                for bi in blocking_intents:
                    try:
                        res = execute_blocking(bi, account=cal_accounts[0], tokens_dir=_tokens_dir(), tz_name=_schedule.timezone)
                    except CalendarError as e:
                        print(f"  ✗  {e}")
                        continue
                    wd = res.start.weekday()
                    day_abbr = (_WEEKDAY_PT[wd] if lang == "pt" else _WEEKDAY_EN[wd])
                    date_label = f"{day_abbr}, {res.start.strftime('%d/%m')}"
                    print(f"  {t('blocking.created', lang, title=res.event_title, date=date_label, start=res.start.strftime(time_fmt), end=res.end.strftime(time_fmt), account=cal_accounts[0])}")
                    if res.conflicts:
                        print(f"  {t('blocking.conflict', lang, titles=', '.join(res.conflicts))}")
            return

        if intent.domain == "workdays":
            from nina.skills.workdays.interpreter import apply as apply_schedule
            from nina.skills.workdays.interpreter import interpret as interpret_schedule
            from nina.skills.workdays.store import save as save_workdays
            schedule_intent = interpret_schedule(line, llm)
            if schedule_intent.action == "update_schedule":
                save_workdays(apply_schedule(schedule_intent, _schedule), _data_dir())
                print(f"  {t('llm.schedule_set', lang)}")
            return

        print(f"  {t('llm.not_understood', lang)}")

    def emptyline(self) -> None:
        pass


def run() -> None:
    NinaConsole().cmdloop()
