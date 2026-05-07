from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class PresenceStatus(str, Enum):
    HOME = "home"  # em casa — disponível normalmente
    WORK = "work"  # trabalho presencial (escritório, campus, cliente…)
    OUT  = "out"   # na rua / em movimento — resumos curtos
    DND  = "dnd"   # não perturbe — silêncio total


@dataclass
class PresenceState:
    status: PresenceStatus
    since: datetime = field(default_factory=lambda: datetime.now(UTC))
    note: str = ""
