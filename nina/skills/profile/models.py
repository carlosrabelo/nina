from dataclasses import dataclass, field

from nina.skills.presence.models import PresenceStatus

_WORK_KEYWORDS  = {"trabalho", "work", "escritório", "escritorio", "office", "profissional"}
_HOME_KEYWORDS  = {"pessoal", "personal", "casa", "home", "particular"}

_PRESENCE_HINTS: dict[str, list[str]] = {
    "office": sorted(_WORK_KEYWORDS),
    "home":   sorted(_HOME_KEYWORDS),
}


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

    def best_calendar_accounts(self, text: str, current_status: PresenceStatus) -> list[str]:
        """Return the most appropriate calendar accounts for *text*.

        Priority:
        1. If text mentions a specific context (work/personal), use that presence.
        2. Use current presence accounts.
        3. Fall back to any non-empty calendar across all presences.
        """
        lower = text.lower()
        for presence_key, keywords in _PRESENCE_HINTS.items():
            if any(kw in lower for kw in keywords):
                accounts = self.mapping.get(presence_key, PresenceProfile()).calendar
                if accounts:
                    return accounts

        accounts = self.for_presence(current_status).calendar
        if accounts:
            return accounts

        # Fallback: any configured calendar
        for p in self.mapping.values():
            if p.calendar:
                return p.calendar
        return []

    def is_empty(self) -> bool:
        return all(
            not p.gmail and not p.calendar
            for p in self.mapping.values()
        )
