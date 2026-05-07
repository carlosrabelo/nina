from dataclasses import dataclass, field
from datetime import time

DAY_NAMES = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
DAY_NAMES_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class WorkDay:
    day: int               # 0=Monday … 6=Sunday
    start: time | None = None
    end: time | None = None
    lunch_start: time | None = None
    lunch_end: time | None = None
    active: bool = False


@dataclass
class WorkSchedule:
    days: list[WorkDay] = field(default_factory=list)
    timezone: str = "America/Sao_Paulo"


@dataclass
class WorkContext:
    is_work_time: bool      # dentro do horário definido (excluindo almoço)
    is_lunch_time: bool     # dentro do horário de almoço
    presence_status: str    # home / work / out / dnd
    label: str              # "home office", "no escritório", "hora extra", etc.
    overtime: bool          # trabalhando além do horário
    weekend_work: bool      # trabalhando no fim de semana


def default_schedule() -> WorkSchedule:
    days = []
    for i in range(7):
        if i < 5:
            days.append(WorkDay(day=i, start=time(9, 0), end=time(18, 0), active=True))
        else:
            days.append(WorkDay(day=i, active=False))
    return WorkSchedule(days=days)
