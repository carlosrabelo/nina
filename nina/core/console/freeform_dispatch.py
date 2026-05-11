"""Natural-language and router dispatch for the Nina console (non-slash commands)."""

from nina.core.console.intent_executors import (
    execute_activity_log_intent,
    execute_memo_intent,
    execute_notification_intent,
)
from nina.core.console.paths import console_lang, data_dir, tokens_dir
from nina.core.i18n import t


def dispatch_natural_language_line(line: str) -> None:
    """Handle a line that is not a registered ``cmd`` command (after ``/`` and ``emailtag`` shortcuts)."""
    lang = console_lang()
    ddir = data_dir()
    tdir = tokens_dir()

    from datetime import datetime
    from zoneinfo import ZoneInfo

    from nina.skills.workdays.store import load as load_workdays

    _wd0 = load_workdays(ddir)
    now_tz = datetime.now(ZoneInfo(_wd0.timezone))

    from nina.skills.memo.interpreter import try_action as memo_try

    result = memo_try(line, lang)
    if result:
        execute_memo_intent(result.action, result.subject, lang, data_dir=ddir)
        return

    from nina.skills.calendar.execute import (
        execute_calendar_read,
        request_from_calendar_intent,
    )
    from nina.skills.calendar.interpreter import try_action as cal_try

    if cal_result := cal_try(line, lang, now=now_tz):
        req = request_from_calendar_intent(cal_result)
        out = execute_calendar_read(
            tokens_dir=tdir,
            data_dir=ddir,
            user_message=line,
            lang=lang,
            req=req,
        )
        for part in out.split("\n"):
            print(f"  {part}")
        return

    from nina.skills.notifications.interpreter import try_action as notif_try

    if notif_result := notif_try(line, lang):
        execute_notification_intent(
            notif_result.action,
            notif_result.minutes,
            notif_result.days,
            lang,
            data_dir=ddir,
        )
        return

    try:
        from nina.core.llm.client import LLMClient

        llm = LLMClient.from_env()
    except Exception:
        print(f"  {t('llm.unavailable', lang)}")
        return

    _schedule = _wd0
    _now = now_tz

    from nina.core.intent.router import route

    intent = route(line, llm, lang=lang, now=_now)

    if intent.domain == "none":
        print(f"  {t('llm.not_understood', lang)}")
        return

    if intent.domain == "presence" and intent.status:
        from nina.skills.presence.models import PresenceState, PresenceStatus
        from nina.skills.presence.store import save as save_presence

        try:
            status = PresenceStatus(intent.status)
        except ValueError:
            print(f"  {t('llm.not_understood', lang)}")
            return
        save_presence(PresenceState(status=status, note=intent.note), ddir)
        label = t(f"presence.label.{status.value}", lang)
        print(f"  {t('llm.presence_set', lang, status=status.value, label=label)}")
        return

    if intent.domain == "memo" and intent.action != "none":
        execute_memo_intent(
            intent.action, intent.subject, lang, data_dir=ddir, due_date=intent.due_date
        )
        return

    if intent.domain == "calendar" and intent.action != "none":
        from nina.skills.calendar.execute import (
            execute_calendar_read,
            request_from_router_intent,
        )

        req = request_from_router_intent(intent)
        out = execute_calendar_read(
            tokens_dir=tdir,
            data_dir=ddir,
            user_message=line,
            lang=lang,
            req=req,
        )
        for part in out.split("\n"):
            print(f"  {part}")
        return

    if intent.domain == "notifications" and intent.action != "none":
        execute_notification_intent(
            intent.action, intent.minutes, intent.days, lang, data_dir=ddir
        )
        return

    if intent.domain == "profile" and intent.updates:
        from nina.skills.profile.interpreter import ProfileIntent, ProfileUpdate
        from nina.skills.profile.interpreter import apply as apply_profile
        from nina.skills.profile.store import load as load_profile
        from nina.skills.profile.store import save as save_profile

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
            profile = load_profile(ddir)
            save_profile(
                apply_profile(
                    ProfileIntent(action="update_profile", updates=updates), profile
                ),
                ddir,
            )
            print(f"  {t('profile.set_ok', lang)}")
        return

    if intent.domain == "activity_log":
        execute_activity_log_intent(intent, tdir, ddir, _now)
        return

    if intent.domain == "blocking":
        from nina.errors import CalendarError
        from nina.skills.calendar.blocking import execute as execute_blocking
        from nina.skills.calendar.blocking import interpret as interpret_blocking
        from nina.skills.presence.store import load as load_presence
        from nina.skills.profile.store import load as load_profile

        blocking_intents = interpret_blocking(line, llm, now=_now)
        if blocking_intents:
            presence = load_presence(ddir)
            profile = load_profile(ddir)
            cal_accounts = profile.best_calendar_accounts(line, presence.status)
            if not cal_accounts:
                print(f"  {t('blocking.no_account', lang)}")
                return
            _WEEKDAY_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
            _WEEKDAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            time_fmt = "%H:%M"
            for bi in blocking_intents:
                try:
                    res = execute_blocking(
                        bi,
                        account=cal_accounts[0],
                        tokens_dir=tdir,
                        tz_name=_schedule.timezone,
                    )
                except CalendarError as e:
                    print(f"  ✗  {e}")
                    continue
                wd = res.start.weekday()
                day_abbr = _WEEKDAY_PT[wd] if lang == "pt" else _WEEKDAY_EN[wd]
                date_label = f"{day_abbr}, {res.start.strftime('%d/%m')}"
                print(
                    f"  {t('blocking.created', lang, title=res.event_title, date=date_label, start=res.start.strftime(time_fmt), end=res.end.strftime(time_fmt), account=cal_accounts[0])}"
                )
                if res.conflicts:
                    print(
                        f"  {t('blocking.conflict', lang, titles=', '.join(res.conflicts))}"
                    )
        return

    if intent.domain == "workdays":
        from nina.skills.workdays.interpreter import apply as apply_schedule
        from nina.skills.workdays.interpreter import interpret as interpret_schedule
        from nina.skills.workdays.store import save as save_workdays

        schedule_intent = interpret_schedule(line, llm)
        if schedule_intent.action == "update_schedule":
            save_workdays(apply_schedule(schedule_intent, _schedule), ddir)
            print(f"  {t('llm.schedule_set', lang)}")
        return

    print(f"  {t('llm.not_understood', lang)}")
