"""Calendar notifications job — reminders and new/changed event detection.

Runs every 5 minutes. Sends via Telegram Bot API (sync HTTP).
Queues notifications when DND or outside work hours; flushes when context allows.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)


def _send_telegram(bot_token: str, owner_id: int, text: str) -> None:
    """Send a message via Telegram Bot API (synchronous)."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = json.dumps({"chat_id": owner_id, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.URLError as e:
        log.warning("telegram send failed: %s", e)


def _format_dt(dt: datetime, lang: str) -> str:
    today = datetime.now(dt.tzinfo).date()
    tomorrow = today + timedelta(days=1)
    if dt.date() == today:
        prefix = "Hoje" if lang == "pt" else "Today"
    elif dt.date() == tomorrow:
        prefix = "Amanhã" if lang == "pt" else "Tomorrow"
    else:
        prefix = dt.strftime("%d/%m") if lang == "pt" else dt.strftime("%m/%d")
    return f"{prefix} {dt.strftime('%H:%M')}"


def _event_key(account: str, event_id: str) -> str:
    return f"{account}:{event_id}"


def make_job(tokens_dir: Path, data_dir: Path, bot_token: str, owner_id: int):  # type: ignore[no-untyped-def]
    """Return the job function bound to the given context."""

    def job() -> None:
        from nina.core.i18n import t
        from nina.core.locale.store import load as load_locale
        from nina.errors import CalendarError
        from nina.integrations.google.auth import discover_accounts
        from nina.integrations.google.calendar.client import CalendarClient
        from nina.skills.notifications.models import KnownEvent, QueuedNotification
        from nina.skills.notifications.store import load as load_state
        from nina.skills.notifications.store import save as save_state
        from nina.skills.presence.models import PresenceStatus
        from nina.skills.presence.store import load as load_presence
        from nina.skills.workdays.checker import get_context
        from nina.skills.workdays.store import load as load_workdays

        lang = load_locale(data_dir).lang
        state = load_state(data_dir)
        schedule = load_workdays(data_dir)
        presence = load_presence(data_dir)
        ctx = get_context(schedule, presence, lang)

        is_dnd = presence.status == PresenceStatus("dnd")
        can_notify = (ctx.is_work_time or ctx.is_lunch_time) and not is_dnd

        tz = ZoneInfo(schedule.timezone)
        now = datetime.now(tz)
        today_str = now.date().isoformat()

        # Clean up reminders_sent entries from previous days
        state.reminders_sent = {
            k: v for k, v in state.reminders_sent.items() if v == today_str
        }

        # ── Lunch reminder ────────────────────────────────────────────────────
        lunch_key = f"lunch:{today_str}"
        if ctx.is_lunch_time and lunch_key not in state.reminders_sent:
            _send_telegram(bot_token, owner_id, t("lunch.reminder", lang))
            state.reminders_sent[lunch_key] = today_str

        notifications_to_send: list[str] = []

        # ── Fetch events from ALL accounts ────────────────────────────────────
        accounts = discover_accounts(tokens_dir)
        watch_end = now + timedelta(days=state.config.watch_days)
        reminder_window_end = now + timedelta(minutes=state.config.reminder_minutes + 5)

        current_event_keys: set[str] = set()

        for account in accounts:
            try:
                client = CalendarClient(account, tokens_dir)
                events = client.list_in_window(now, watch_end)
            except CalendarError as e:
                log.warning("calendar fetch failed for %s: %s", account, e)
                continue

            for event in events:
                key = _event_key(account, event.event_id)
                current_event_keys.add(key)

                # ── Reminder check ────────────────────────────────────────────
                if event.start <= reminder_window_end and event.start >= now:
                    reminder_key = f"{key}:{today_str}"
                    if reminder_key not in state.reminders_sent:
                        minutes_until = int((event.start - now).total_seconds() / 60)
                        start_str = event.start.strftime("%H:%M")
                        end_str = event.end.strftime("%H:%M")
                        if lang == "pt":
                            msg = f"🔔 Em {minutes_until} min: {event.title}\n{start_str} → {end_str}"
                        else:
                            msg = f"🔔 In {minutes_until} min: {event.title}\n{start_str} → {end_str}"
                        notifications_to_send.append(msg)
                        state.reminders_sent[reminder_key] = today_str

                # ── New / modified event check ─────────────────────────────────
                known = state.known_events.get(key)
                updated_str = getattr(event, "updated", "") or ""
                start_str = event.start.isoformat() if event.start else ""
                end_str = event.end.isoformat() if event.end else ""

                if known is None:
                    # New event
                    dt_label = _format_dt(event.start, lang)
                    end_time = event.end.strftime("%H:%M") if event.end else ""
                    if lang == "pt":
                        msg = f"📅 Novo evento: {event.title}\n{dt_label} → {end_time}  |  {account}"
                    else:
                        msg = f"📅 New event: {event.title}\n{dt_label} → {end_time}  |  {account}"
                    notifications_to_send.append(msg)
                    state.known_events[key] = KnownEvent(
                        event_id=event.event_id,
                        account=account,
                        title=event.title,
                        start=start_str,
                        end=end_str,
                        updated=updated_str,
                    )
                else:
                    # Check for modifications
                    title_changed = known.title != event.title
                    time_changed = known.start != start_str or known.end != end_str
                    if title_changed or time_changed:
                        dt_label = _format_dt(event.start, lang)
                        end_time = event.end.strftime("%H:%M") if event.end else ""
                        if lang == "pt":
                            msg = f"✏️ Evento alterado: {event.title}\nAntes: {known.start[11:16]} → {known.end[11:16]}\nAgora: {dt_label} → {end_time}  |  {account}"
                        else:
                            msg = f"✏️ Event updated: {event.title}\nBefore: {known.start[11:16]} → {known.end[11:16]}\nNow: {dt_label} → {end_time}  |  {account}"
                        notifications_to_send.append(msg)
                        state.known_events[key] = KnownEvent(
                            event_id=event.event_id,
                            account=account,
                            title=event.title,
                            start=start_str,
                            end=end_str,
                            updated=updated_str,
                        )

        # ── Detect cancelled events ───────────────────────────────────────────
        for key, known in list(state.known_events.items()):
            if key not in current_event_keys:
                # Only notify if event was in the future when we last saw it
                try:
                    last_start = datetime.fromisoformat(known.start).replace(tzinfo=tz)
                    if last_start > now:
                        if lang == "pt":
                            msg = f"❌ Evento cancelado: {known.title}\nEra: {known.start[11:16]} → {known.end[11:16]}  |  {known.account}"
                        else:
                            msg = f"❌ Event cancelled: {known.title}\nWas: {known.start[11:16]} → {known.end[11:16]}  |  {known.account}"
                        notifications_to_send.append(msg)
                except (ValueError, TypeError):
                    pass
                del state.known_events[key]

        # ── Send or queue ─────────────────────────────────────────────────────
        flushing = can_notify and not state.last_can_notify

        if can_notify:
            # Flush queued notifications first (if we just became able to notify)
            if flushing and state.queue:
                if lang == "pt":
                    header = f"📬 {len(state.queue)} notificação(ões) pendente(s):"
                else:
                    header = f"📬 {len(state.queue)} pending notification(s):"
                _send_telegram(bot_token, owner_id, header)
                for queued in state.queue:
                    _send_telegram(bot_token, owner_id, queued.message)
                state.queue.clear()

            # Send current notifications
            for msg in notifications_to_send:
                _send_telegram(bot_token, owner_id, msg)
        else:
            # Queue for later
            existing_ids = {q.id for q in state.queue}
            for msg in notifications_to_send:
                qid = str(hash(msg))
                if qid not in existing_ids:
                    state.queue.append(QueuedNotification(id=qid, message=msg))

        state.last_can_notify = can_notify
        save_state(state, data_dir)

    return job
