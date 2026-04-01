from datetime import datetime
from zoneinfo import ZoneInfo

from nina.skills.presence.models import PresenceState, PresenceStatus
from nina.skills.workdays.models import WorkContext, WorkSchedule


def get_context(
    schedule: WorkSchedule, presence: PresenceState, lang: str = "pt"
) -> WorkContext:
    from nina.core.i18n import t

    now = datetime.now(ZoneInfo(schedule.timezone))
    day_of_week = now.weekday()  # 0=Monday
    current_time = now.time().replace(tzinfo=None)

    work_day = next(
        (d for d in schedule.days if d.day == day_of_week and d.active),
        None,
    )

    is_lunch_time = (
        work_day is not None
        and work_day.lunch_start is not None
        and work_day.lunch_end is not None
        and work_day.lunch_start <= current_time <= work_day.lunch_end
    )

    is_work_time = (
        work_day is not None
        and work_day.start is not None
        and work_day.end is not None
        and work_day.start <= current_time <= work_day.end
        and not is_lunch_time
    )

    is_weekend = day_of_week >= 5
    at_work = presence.status in (PresenceStatus.OFFICE, PresenceStatus.HOME)

    overtime = (
        at_work
        and work_day is not None
        and work_day.end is not None
        and current_time > work_day.end
    )

    # Only OFFICE on a weekend is "weekend work" — HOME on a weekend is just off hours
    weekend_work = presence.status == PresenceStatus.OFFICE and is_weekend

    if presence.status == PresenceStatus.DND:
        label = t("context.label.dnd", lang)
    elif presence.status == PresenceStatus.OUT:
        label = t("context.label.out", lang)
    elif is_lunch_time:
        label = t("context.label.lunch", lang)
    elif weekend_work:
        label = t("context.label.weekend_work", lang)
    elif overtime:
        label = t("context.label.overtime", lang)
    elif presence.status == PresenceStatus.HOME and is_work_time:
        label = t("context.label.home_office", lang)
    elif presence.status == PresenceStatus.OFFICE and is_work_time:
        label = t("context.label.office", lang)
    elif not is_work_time:
        label = t("context.label.off_hours", lang)
    else:
        label = presence.status.value

    return WorkContext(
        is_work_time=is_work_time,
        is_lunch_time=is_lunch_time,
        presence_status=presence.status.value,
        label=label,
        overtime=overtime,
        weekend_work=weekend_work,
    )
