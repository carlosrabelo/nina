"""End-of-day prompt logic — trigger when presence changes from work → home/out.

Detects presence transitions and sends a prompt via Telegram asking
what the user did during the day.
"""

from __future__ import annotations

from nina.skills.presence.models import PresenceStatus

# Transitions that trigger an end-of-day prompt
_EOD_TRIGGERS = {
    (PresenceStatus.WORK, PresenceStatus.HOME),
    (PresenceStatus.WORK, PresenceStatus.OUT),
    (PresenceStatus.WORK, PresenceStatus.DND),
}

# Prompt messages
_PROMPT_PT = "Saiu do trabalho. O que você fez hoje?\nEx: reunião com cliente 9h-10h, deploy 10h-12h, code review à tarde"
_PROMPT_EN = "Left work. What did you do today?\nEx: meeting with client 9h-10h, deploy 10h-12h, code review afternoon"


def should_prompt_eod(old_status: PresenceStatus, new_status: PresenceStatus) -> bool:
    """Check if a presence change should trigger an end-of-day prompt."""
    return (old_status, new_status) in _EOD_TRIGGERS


def get_eod_prompt(lang: str = "pt") -> str:
    """Get the end-of-day prompt text."""
    return _PROMPT_PT if lang == "pt" else _PROMPT_EN
