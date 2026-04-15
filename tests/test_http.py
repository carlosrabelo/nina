# tests/test_http.py
"""Tests for the FastAPI HTTP daemon — auth, presence shortcut, flat status."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nina.core.daemon.http import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(tokens_dir=tmp_path / "tokens", data_dir=tmp_path)
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture()
def secured_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("NINA_API_KEY", "secret123")
    app = create_app(tokens_dir=tmp_path / "tokens", data_dir=tmp_path)
    return TestClient(app, raise_server_exceptions=True)


# ── API key auth ──────────────────────────────────────────────────────────────


class TestApiKeyAuth:
    def test_no_key_configured_allows_requests(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.status_code == 200

    def test_valid_key_allows_request(self, secured_client: TestClient) -> None:
        r = secured_client.get("/health", headers={"x-api-key": "secret123"})
        assert r.status_code == 200

    def test_wrong_key_returns_403(self, secured_client: TestClient) -> None:
        r = secured_client.get("/health", headers={"x-api-key": "wrong"})
        assert r.status_code == 403
        assert r.json()["detail"] == "invalid_api_key"

    def test_missing_key_returns_403(self, secured_client: TestClient) -> None:
        r = secured_client.get("/health")
        assert r.status_code == 403

    def test_key_required_for_presence(self, secured_client: TestClient) -> None:
        r = secured_client.get("/presence")
        assert r.status_code == 403

    def test_key_required_for_status(self, secured_client: TestClient) -> None:
        r = secured_client.get("/status")
        assert r.status_code == 403

    def test_key_required_for_presence_path(self, secured_client: TestClient) -> None:
        r = secured_client.post("/presence/work")
        assert r.status_code == 403


# ── POST /presence/{status} ───────────────────────────────────────────────────


class TestPresencePath:
    def test_set_work_status(self, client: TestClient) -> None:
        r = client.post("/presence/work")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "work"
        assert data["note"] == ""
        assert "since" in data

    def test_set_home_with_note(self, client: TestClient) -> None:
        r = client.post("/presence/home", params={"note": "chegou em casa"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "home"
        assert data["note"] == "chegou em casa"

    def test_invalid_status_returns_422(self, client: TestClient) -> None:
        r = client.post("/presence/invalid_xyz")
        assert r.status_code == 422
        assert r.json()["detail"] == "invalid_status"

    def test_persists_presence(self, client: TestClient) -> None:
        client.post("/presence/out")
        r = client.get("/presence")
        assert r.status_code == 200
        assert r.json()["status"] == "out"

    def test_note_persists(self, client: TestClient) -> None:
        client.post("/presence/work", params={"note": "no escritório"})
        r = client.get("/presence")
        assert r.json()["note"] == "no escritório"


# ── GET /status ───────────────────────────────────────────────────────────────


class TestFlatStatus:
    def test_returns_expected_keys(self, client: TestClient) -> None:
        r = client.get("/status")
        assert r.status_code == 200
        data = r.json()
        assert "presence" in data
        assert "note" in data
        assert "since" in data
        assert "label" in data
        assert "is_work_time" in data
        assert "is_lunch_time" in data
        assert "overtime" in data
        assert "weekend_work" in data

    def test_reflects_current_presence(self, client: TestClient) -> None:
        client.post("/presence/home")
        r = client.get("/status")
        assert r.json()["presence"] == "home"

    def test_note_reflected(self, client: TestClient) -> None:
        client.post("/presence/work", params={"note": "test note"})
        r = client.get("/status")
        assert r.json()["note"] == "test note"

    def test_boolean_fields_are_bool(self, client: TestClient) -> None:
        r = client.get("/status")
        data = r.json()
        assert isinstance(data["is_work_time"], bool)
        assert isinstance(data["is_lunch_time"], bool)
        assert isinstance(data["overtime"], bool)
        assert isinstance(data["weekend_work"], bool)
