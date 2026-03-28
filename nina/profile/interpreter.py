"""Interpret free-text messages and extract profile account mappings using the LLM."""

import json
import re
from dataclasses import dataclass, field

from nina.llm.client import LLMClient
from nina.presence.models import PresenceStatus
from nina.profile.models import Profile

_SYSTEM_PROMPT = """You are an assistant that interprets account-to-presence mappings from natural language.

Presence statuses: home, office, out, dnd.
Services: gmail, calendar.

Analyze the user's message and return a JSON object with:
- "action": "update_profile" if the message describes account assignments, otherwise "none"
- "updates": list of objects, each with:
  - "presence": one of "home", "office", "out", "dnd"
  - "gmail": list of email addresses (empty list if not mentioned)
  - "calendar": list of email addresses or calendar IDs (empty list if not mentioned)

Return ONLY valid JSON, no explanation, no markdown.

Examples:
"quando estiver no escritório usar work@empresa.com"
-> {"action": "update_profile", "updates": [{"presence": "office", "gmail": ["work@empresa.com"], "calendar": []}]}

"em casa uso pessoal@gmail.com para email e calendario"
-> {"action": "update_profile", "updates": [{"presence": "home", "gmail": ["pessoal@gmail.com"], "calendar": ["pessoal@gmail.com"]}]}

"office: work@co.com, home: me@gmail.com"
-> {"action": "update_profile", "updates": [
     {"presence": "office", "gmail": ["work@co.com"], "calendar": []},
     {"presence": "home",   "gmail": ["me@gmail.com"], "calendar": []}
   ]}

"quando sair de casa uso meu email pessoal@gmail.com"
-> {"action": "update_profile", "updates": [{"presence": "out", "gmail": ["pessoal@gmail.com"], "calendar": []}]}

"Qual é o tempo hoje?"
-> {"action": "none"}
"""


@dataclass
class ProfileUpdate:
    presence: str
    gmail: list[str] = field(default_factory=list)
    calendar: list[str] = field(default_factory=list)


@dataclass
class ProfileIntent:
    action: str                       # "update_profile" | "none"
    updates: list[ProfileUpdate] = field(default_factory=list)


def interpret(text: str, llm: LLMClient) -> ProfileIntent:
    """Parse *text* and return a ProfileIntent. Never raises."""
    try:
        raw = llm.complete(text, system=_SYSTEM_PROMPT)
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(raw)
    except Exception:
        return ProfileIntent(action="none")

    if data.get("action") != "update_profile":
        return ProfileIntent(action="none")

    updates: list[ProfileUpdate] = []
    for item in data.get("updates", []):
        try:
            presence = item["presence"]
            PresenceStatus(presence)  # validate
            updates.append(ProfileUpdate(
                presence=presence,
                gmail=list(item.get("gmail", [])),
                calendar=list(item.get("calendar", [])),
            ))
        except (KeyError, ValueError):
            continue

    if not updates:
        return ProfileIntent(action="none")

    return ProfileIntent(action="update_profile", updates=updates)


def apply(intent: ProfileIntent, profile: Profile) -> Profile:
    """Apply a ProfileIntent to an existing Profile (mutated in place)."""
    from nina.profile.models import PresenceProfile
    for update in intent.updates:
        existing = profile.mapping.get(update.presence, PresenceProfile())
        if update.gmail:
            existing.gmail = update.gmail
        if update.calendar:
            existing.calendar = update.calendar
        profile.mapping[update.presence] = existing
    return profile
