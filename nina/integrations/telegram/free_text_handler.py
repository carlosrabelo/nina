"""Telegram free-text: pattern match + unified LLM router (mirrors console freeform)."""

from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from nina.core.i18n import t


def format_notification_intent_reply(
    action: str, minutes: int | None, days: int | None, lang: str, data_dir: Path
) -> str:
    from nina.skills.notifications.store import load as load_notif
    from nina.skills.notifications.store import save as save_notif

    state = load_notif(data_dir)
    if action == "get":
        return t(
            "notify.config",
            lang,
            reminder_minutes=state.config.reminder_minutes,
            watch_days=state.config.watch_days,
        )
    if action == "set_reminder" and minutes is not None:
        state.config.reminder_minutes = minutes
        save_notif(state, data_dir)
        return t("notify.reminder_set", lang, minutes=minutes)
    if action == "set_days" and days is not None:
        state.config.watch_days = days
        save_notif(state, data_dir)
        return t("notify.days_set", lang, days=days)
    return t("notify.usage", lang)


def format_memo_intent_reply(
    action: str, subject: str, lang: str, data_dir: Path, due_date: str = ""
) -> str:
    from nina.core.store.db import open_db
    from nina.core.store.models import Memo
    from nina.core.store.repos import memo as memo_repo

    conn = open_db(data_dir)
    if action == "list":
        memos = memo_repo.list_open(conn)
        if not memos:
            return t("memo.none_open", lang)
        lines = []
        for m in memos:
            due = t("memo.due", lang, date=m.due_date) if m.due_date else ""
            lines.append(f"[{m.id[:8]}] {m.text}{due}")
        return "\n".join(lines)
    if action == "remind":
        memo_repo.add(conn, Memo(text=subject, due_date=due_date or None))
        if due_date:
            return t("memo.remind_set", lang, date=due_date, subject=subject)
        return t("memo.saved", lang)
    matches = [m for m in memo_repo.list_open(conn) if subject.lower() in m.text.lower()]
    if not matches:
        return t("memo.not_found", lang)
    lines = []
    for m in matches:
        if action == "close":
            memo_repo.done(conn, m.id)
            lines.append(f"{t('memo.done', lang)} — {m.text}")
        elif action == "dismiss":
            memo_repo.dismiss(conn, m.id)
            lines.append(f"{t('memo.dismissed', lang)} — {m.text}")
    return "\n".join(lines)


def format_activity_log_reply(
    intent, tokens_dir: Path, data_dir: Path, tz_name: str,
) -> str:
    from nina.skills.activity_log.google_reader import (
        get_summary,
        query_activities,
        query_by_keyword,
    )
    from nina.skills.activity_log.google_writer import log_activity
    from nina.skills.activity_log.models import ActivityIntent
    from nina.skills.presence.store import load as load_presence
    from nina.skills.profile.store import load as load_profile

    presence = load_presence(data_dir)
    profile = load_profile(data_dir)
    cal_accounts = profile.for_presence(presence.status).calendar
    if not cal_accounts:
        return "Nenhuma conta de calendar configurada."

    action = intent.entities.get("query_type", "") or intent.action

    if action == "log":
        ai = ActivityIntent(
            action="log",
            title=intent.entities.get("title", ""),
            duration_minutes=intent.entities.get("duration_minutes", 60),
        )
        result = log_activity(ai, cal_accounts[0], tokens_dir, tz_name)
        return result.message

    if action in ("query", "summary"):
        keyword = intent.entities.get("query_keyword", "")
        if action == "summary":
            summary = get_summary(cal_accounts[0], tokens_dir)
            lines = [summary.period_label, f"Total: {summary.total_minutes} min"]
            for kw, mins in sorted(summary.by_keyword.items(), key=lambda x: -x[1]):
                lines.append(f"  {kw}: {mins} min")
            return "\n".join(lines)

        if keyword:
            entries = query_by_keyword(cal_accounts[0], tokens_dir, keyword)
        else:
            entries = query_activities(cal_accounts[0], tokens_dir)

        if not entries:
            return "Nenhuma atividade encontrada."
        lines = []
        for e in entries:
            start_label = e.start.strftime("%d/%m %H:%M")
            end_label = e.end.strftime("%H:%M")
            lines.append(f"{start_label} → {end_label}  {e.title}")
        return "\n".join(lines)

    return "Não entendi a atividade."


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from nina.errors import CalendarError, LLMError
    from nina.integrations.telegram.command_registry import bot_lang

    lang = bot_lang(ctx)
    tokens_dir: Path = ctx.bot_data["tokens_dir"]
    data_dir: Path = ctx.bot_data["data_dir"]
    text = update.message.text or ""

    from datetime import datetime
    from zoneinfo import ZoneInfo

    from nina.skills.workdays.store import load as load_workdays

    _wd0 = load_workdays(data_dir)
    now_tz = datetime.now(ZoneInfo(_wd0.timezone))

    from nina.skills.memo.interpreter import try_action as memo_try

    if result := memo_try(text, lang):
        await update.message.reply_text(
            format_memo_intent_reply(result.action, result.subject, lang, data_dir)
        )
        return

    from nina.skills.calendar.execute import (
        execute_calendar_read,
        request_from_calendar_intent,
    )
    from nina.skills.calendar.interpreter import try_action as cal_try

    if cal_result := cal_try(text, lang, now=now_tz):
        req = request_from_calendar_intent(cal_result)
        await update.message.reply_text(
            execute_calendar_read(
                tokens_dir=tokens_dir,
                data_dir=data_dir,
                user_message=text,
                lang=lang,
                req=req,
            )
        )
        return

    from nina.skills.notifications.interpreter import try_action as notif_try

    if notif_result := notif_try(text, lang):
        await update.message.reply_text(
            format_notification_intent_reply(
                notif_result.action,
                notif_result.minutes,
                notif_result.days,
                lang,
                data_dir,
            )
        )
        return

    try:
        from nina.core.llm.client import LLMClient

        llm = LLMClient.from_env()
    except (LLMError, Exception):
        await update.message.reply_text(t("llm.unavailable", lang))
        return

    _schedule = _wd0
    _now = now_tz

    from nina.core.intent.router import route

    intent = route(text, llm, lang=lang, now=_now)

    if intent.domain == "none":
        await update.message.reply_text(t("llm.not_understood", lang))
        return

    if intent.domain == "presence" and intent.status:
        from nina.skills.presence.models import PresenceState, PresenceStatus
        from nina.skills.presence.store import save as save_presence

        try:
            status = PresenceStatus(intent.status)
        except ValueError:
            await update.message.reply_text(t("llm.not_understood", lang))
            return
        save_presence(PresenceState(status=status, note=intent.note), data_dir)
        label = t(f"presence.label.{status.value}", lang)
        await update.message.reply_text(
            t("llm.presence_set", lang, status=status.value, label=label)
        )
        return

    if intent.domain == "memo" and intent.action != "none":
        await update.message.reply_text(
            format_memo_intent_reply(
                intent.action, intent.subject, lang, data_dir, intent.due_date
            )
        )
        return

    if intent.domain == "calendar" and intent.action != "none":
        from nina.skills.calendar.execute import (
            execute_calendar_read,
            request_from_router_intent,
        )

        req = request_from_router_intent(intent)
        await update.message.reply_text(
            execute_calendar_read(
                tokens_dir=tokens_dir,
                data_dir=data_dir,
                user_message=text,
                lang=lang,
                req=req,
            )
        )
        return

    if intent.domain == "notifications" and intent.action != "none":
        await update.message.reply_text(
            format_notification_intent_reply(
                intent.action, intent.minutes, intent.days, lang, data_dir
            )
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
            profile = load_profile(data_dir)
            save_profile(
                apply_profile(
                    ProfileIntent(action="update_profile", updates=updates), profile
                ),
                data_dir,
            )
            await update.message.reply_text(t("profile.set_ok", lang))
        return

    if intent.domain == "activity_log":
        await update.message.reply_text(
            format_activity_log_reply(
                intent, tokens_dir, data_dir, _schedule.timezone
            )
        )
        return

    if intent.domain == "blocking":
        from nina.skills.calendar.blocking import execute as execute_blocking
        from nina.skills.calendar.blocking import interpret as interpret_blocking
        from nina.skills.presence.store import load as load_presence
        from nina.skills.profile.store import load as load_profile

        blocking_intents = interpret_blocking(text, llm, now=_now)
        if blocking_intents:
            presence = load_presence(data_dir)
            profile = load_profile(data_dir)
            cal_accounts = profile.best_calendar_accounts(text, presence.status)
            if not cal_accounts:
                await update.message.reply_text(t("blocking.no_account", lang))
                return
            _WEEKDAY_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
            _WEEKDAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            time_fmt = "%H:%M"
            for bi in blocking_intents:
                try:
                    res = execute_blocking(
                        bi,
                        account=cal_accounts[0],
                        tokens_dir=tokens_dir,
                        tz_name=_schedule.timezone,
                    )
                except CalendarError as e:
                    await update.message.reply_text(f"✗ {e}")
                    continue
                wd = res.start.weekday()
                day_abbr = _WEEKDAY_PT[wd] if lang == "pt" else _WEEKDAY_EN[wd]
                date_label = f"{day_abbr}, {res.start.strftime('%d/%m')}"
                reply = t(
                    "blocking.created",
                    lang,
                    title=res.event_title,
                    date=date_label,
                    start=res.start.strftime(time_fmt),
                    end=res.end.strftime(time_fmt),
                    account=cal_accounts[0],
                )
                if res.conflicts:
                    reply += "\n" + t("blocking.conflict", lang, titles=", ".join(res.conflicts))
                await update.message.reply_text(reply)
        return

    if intent.domain == "workdays":
        from nina.skills.workdays.interpreter import apply as apply_schedule
        from nina.skills.workdays.interpreter import interpret as interpret_schedule
        from nina.skills.workdays.store import save as save_workdays

        schedule_intent = interpret_schedule(text, llm)
        if schedule_intent.action == "update_schedule":
            save_workdays(apply_schedule(schedule_intent, _schedule), data_dir)
            await update.message.reply_text(t("llm.schedule_set", lang))
        return

    await update.message.reply_text(t("llm.not_understood", lang))
