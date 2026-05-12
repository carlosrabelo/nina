"""Console-side execution of interpreted intents (print to stdout)."""

from pathlib import Path

from nina.core.i18n import t


def execute_notification_intent(
    action: str, minutes: int | None, days: int | None, lang: str, *, data_dir: Path
) -> None:
    from nina.skills.notifications.store import load as load_notif
    from nina.skills.notifications.store import save as save_notif

    state = load_notif(data_dir)
    if action == "get":
        print(
            f"  {t('notify.config', lang, reminder_minutes=state.config.reminder_minutes, watch_days=state.config.watch_days)}"
        )
        return
    if action == "set_reminder" and minutes is not None:
        state.config.reminder_minutes = minutes
        save_notif(state, data_dir)
        print(f"  {t('notify.reminder_set', lang, minutes=minutes)}")
        return
    if action == "set_days" and days is not None:
        state.config.watch_days = days
        save_notif(state, data_dir)
        print(f"  {t('notify.days_set', lang, days=days)}")
        return
    print(f"  {t('notify.usage', lang)}")


def execute_activity_log_intent(
    intent, tokens_dir: Path, data_dir: Path, now
) -> None:
    """Execute an activity_log intent (log or query)."""
    from nina.skills.presence.store import load as load_presence
    from nina.skills.profile.store import load as load_profile

    action = intent.entities.get("query_type", "") or intent.action

    if action == "log" or intent.action == "log":
        presence = load_presence(data_dir)
        profile = load_profile(data_dir)
        cal_accounts = profile.for_presence(presence.status).calendar
        if not cal_accounts:
            print("  Nenhuma conta de calendar configurada.")
            return
        from nina.skills.activity_log import models as act_models
        from nina.skills.activity_log.google_writer import log_activity

        ai = act_models.ActivityIntent(
            action="log",
            title=intent.entities.get("title", ""),
            duration_minutes=intent.entities.get("duration_minutes", 60),
        )
        start_str = intent.entities.get("start")
        end_str = intent.entities.get("end")
        if start_str:
            from datetime import datetime as dt

            parts = start_str.replace("T", " ").split(":")
            sh = int(parts[0])
            sm = int(parts[1]) if len(parts) > 1 else 0
            ai.start = dt(
                now.date().year,
                now.date().month,
                now.date().day,
                sh,
                sm,
            )
        if end_str:
            from datetime import datetime as dt

            parts = end_str.replace("T", " ").split(":")
            eh = int(parts[0])
            em = int(parts[1]) if len(parts) > 1 else 0
            ai.end = dt(
                now.date().year,
                now.date().month,
                now.date().day,
                eh,
                em,
            )
        result = log_activity(ai, cal_accounts[0], tokens_dir)
        print(f"  {result.message}")
        if result.link:
            print(f"  {result.link}")
        return

    if action in ("query", "summary"):
        presence = load_presence(data_dir)
        profile = load_profile(data_dir)
        cal_accounts = profile.for_presence(presence.status).calendar
        if not cal_accounts:
            print("  Nenhuma conta de calendar configurada.")
            return
        from nina.skills.activity_log.google_reader import (
            get_summary,
            query_activities,
            query_by_keyword,
        )

        keyword = intent.entities.get("query_keyword", "")
        query_date = None
        qd_str = intent.entities.get("query_date")
        if qd_str:
            from datetime import date

            try:
                parts = qd_str.split("-")
                query_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, IndexError):
                pass

        if action == "summary":
            summary = get_summary(cal_accounts[0], tokens_dir)
            print(f"  {summary.period_label}")
            print(f"  Total: {summary.total_minutes} min")
            if summary.by_keyword:
                for kw, mins in sorted(summary.by_keyword.items(), key=lambda x: -x[1]):
                    print(f"    {kw}: {mins} min")
            return

        if keyword:
            entries = query_by_keyword(cal_accounts[0], tokens_dir, keyword)
        elif query_date:
            entries = query_activities(
                cal_accounts[0],
                tokens_dir,
                target_date=query_date,
            )
        else:
            entries = query_activities(cal_accounts[0], tokens_dir)

        if not entries:
            print("  Nenhuma atividade encontrada.")
            return
        for e in entries:
            start_label = e.start.strftime("%d/%m %H:%M")
            end_label = e.end.strftime("%H:%M")
            print(f"  {start_label} → {end_label}  {e.title}")
        return

    print("  Não entendi a atividade.")


def execute_email_label_intent(
    action: str, target_id: str, label_name: str, lang: str, *, data_dir: Path, tokens_dir: Path
) -> None:
    from nina.skills.email_label.execute import (
        dismiss_all_pending_labels,
        dismiss_pending_by_prefix,
        format_pending_list,
        teach_label_for_pending,
    )

    if action == "list":
        text = format_pending_list(data_dir)
        for part in text.split("\n"):
            print(f"  {part}")
        return
    if action == "dismiss_all":
        out = dismiss_all_pending_labels(data_dir)
        print(f"  {out}")
        return
    if action == "dismiss" and target_id:
        out = dismiss_pending_by_prefix(data_dir, target_id)
        print(f"  {out}")
        return
    if action == "teach" and target_id and label_name:
        out = teach_label_for_pending(tokens_dir, data_dir, target_id, label_name)
        print(f"  {out}")
        return
    from nina.core.i18n import t as _t
    print(f"  {_t('email_label.usage', lang)}")


def execute_memo_intent(
    action: str, subject: str, lang: str, *, data_dir: Path, due_date: str = ""
) -> None:
    from nina.core.store.db import open_db
    from nina.core.store.models import Memo
    from nina.core.store.repos import memo as memo_repo

    conn = open_db(data_dir)
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
