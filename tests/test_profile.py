# tests/test_profile.py
"""Tests for the profile domain."""

from pathlib import Path
from unittest.mock import MagicMock

from nina.skills.presence.models import PresenceStatus
from nina.skills.profile.interpreter import ProfileIntent, ProfileUpdate, apply, interpret
from nina.skills.profile.models import PresenceProfile, Profile
from nina.skills.profile.store import load, save


class TestProfileStore:
    def test_load_returns_empty_when_no_file(self, tmp_path: Path) -> None:
        profile = load(tmp_path)
        assert profile.is_empty()

    def test_save_then_load(self, tmp_path: Path) -> None:
        profile = Profile(mapping={
            "work": PresenceProfile(gmail=["work@co.com"], calendar=["work@co.com"]),
            "home": PresenceProfile(gmail=["me@gmail.com"], calendar=[]),
        })
        save(profile, tmp_path)
        loaded = load(tmp_path)
        assert loaded.for_presence(PresenceStatus.WORK).gmail == ["work@co.com"]
        assert loaded.for_presence(PresenceStatus.HOME).gmail == ["me@gmail.com"]
        assert loaded.for_presence(PresenceStatus.HOME).calendar == []

    def test_for_presence_returns_empty_profile_when_not_configured(self, tmp_path: Path) -> None:
        profile = load(tmp_path)
        p = profile.for_presence(PresenceStatus.OUT)
        assert p.gmail == []
        assert p.calendar == []


class TestProfileInterpreter:
    def _llm(self, response: str) -> MagicMock:
        llm = MagicMock()
        llm.complete.return_value = response
        return llm

    def test_set_work_gmail(self) -> None:
        payload = '{"action": "update_profile", "updates": [{"presence": "work", "gmail": ["work@co.com"], "calendar": []}]}'
        result = interpret("no escritório usar work@co.com", self._llm(payload))
        assert result.action == "update_profile"
        assert result.updates[0].presence == "work"
        assert result.updates[0].gmail == ["work@co.com"]

    def test_set_home_gmail_and_calendar(self) -> None:
        payload = '{"action": "update_profile", "updates": [{"presence": "home", "gmail": ["me@gmail.com"], "calendar": ["me@gmail.com"]}]}'
        result = interpret("em casa uso me@gmail.com", self._llm(payload))
        assert result.updates[0].gmail == ["me@gmail.com"]
        assert result.updates[0].calendar == ["me@gmail.com"]

    def test_multiple_updates(self) -> None:
        payload = '{"action": "update_profile", "updates": [{"presence": "work", "gmail": ["w@co.com"], "calendar": []}, {"presence": "home", "gmail": ["me@gmail.com"], "calendar": []}]}'
        result = interpret("work w@co.com, home me@gmail.com", self._llm(payload))
        assert len(result.updates) == 2

    def test_action_none(self) -> None:
        result = interpret("Qual é o tempo?", self._llm('{"action": "none"}'))
        assert result.action == "none"

    def test_invalid_presence_skipped(self) -> None:
        payload = '{"action": "update_profile", "updates": [{"presence": "flying", "gmail": ["x@x.com"], "calendar": []}]}'
        result = interpret("qualquer coisa", self._llm(payload))
        assert result.action == "none"

    def test_invalid_json_returns_none(self) -> None:
        result = interpret("qualquer coisa", self._llm("not json"))
        assert result.action == "none"


class TestApplyProfile:
    def test_sets_gmail(self) -> None:
        profile = Profile()
        intent = ProfileIntent(action="update_profile", updates=[
            ProfileUpdate(presence="work", gmail=["work@co.com"]),
        ])
        apply(intent, profile)
        assert profile.for_presence(PresenceStatus.WORK).gmail == ["work@co.com"]

    def test_preserves_existing_calendar_when_not_in_update(self) -> None:
        profile = Profile(mapping={
            "work": PresenceProfile(gmail=["old@co.com"], calendar=["cal@co.com"]),
        })
        intent = ProfileIntent(action="update_profile", updates=[
            ProfileUpdate(presence="work", gmail=["new@co.com"]),
        ])
        apply(intent, profile)
        assert profile.for_presence(PresenceStatus.WORK).gmail == ["new@co.com"]
        assert profile.for_presence(PresenceStatus.WORK).calendar == ["cal@co.com"]

    def test_sets_multiple_presences(self) -> None:
        profile = Profile()
        intent = ProfileIntent(action="update_profile", updates=[
            ProfileUpdate(presence="work", gmail=["work@co.com"]),
            ProfileUpdate(presence="home", gmail=["me@gmail.com"]),
        ])
        apply(intent, profile)
        assert profile.for_presence(PresenceStatus.WORK).gmail == ["work@co.com"]
        assert profile.for_presence(PresenceStatus.HOME).gmail == ["me@gmail.com"]
