from dataclasses import dataclass, field

from nina.presence.models import PresenceStatus


@dataclass
class PresenceProfile:
    """Accounts active for a given presence status."""
    gmail: list[str] = field(default_factory=list)
    calendar: list[str] = field(default_factory=list)
    # Future: slack, github, notion, ...


@dataclass
class Profile:
    """Maps each presence status to its active service accounts."""
    mapping: dict[str, PresenceProfile] = field(default_factory=dict)

    def for_presence(self, status: PresenceStatus) -> PresenceProfile:
        return self.mapping.get(status.value, PresenceProfile())

    def is_empty(self) -> bool:
        return all(
            not p.gmail and not p.calendar
            for p in self.mapping.values()
        )
