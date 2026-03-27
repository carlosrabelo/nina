# tests/test_llm.py
"""Unit tests for llm client — all LLM calls are mocked."""

import os
from unittest.mock import MagicMock, patch

import pytest

from nina.errors import LLMError
from nina.llm.client import LLMClient, Message

_LLM_KEYS = {"LLM_MODEL", "LLM_TEMPERATURE", "LLM_MAX_TOKENS", "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"}


def _clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in _LLM_KEYS}


def test_message_fields():
    m = Message(role="user", content="hello")
    assert m.role == "user"
    assert m.content == "hello"


def _mock_response(text: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_chat_returns_content():
    client = LLMClient(model="groq/llama-3.3-70b-versatile")
    messages = [Message("user", "say hi")]
    with patch("litellm.completion", return_value=_mock_response("hi")) as mock_call:
        result = client.chat(messages)
    assert result == "hi"
    mock_call.assert_called_once()


def test_chat_passes_model_and_params():
    client = LLMClient(model="openai/gpt-4o-mini", temperature=0.7, max_tokens=512)
    with patch("litellm.completion", return_value=_mock_response("x")) as mock_call:
        client.chat([Message("user", "test")])
    call_kwargs = mock_call.call_args.kwargs
    assert call_kwargs["model"] == "openai/gpt-4o-mini"
    assert call_kwargs["temperature"] == 0.7
    assert call_kwargs["max_tokens"] == 512


def test_chat_raises_llm_error_on_exception():
    client = LLMClient(model="groq/llama-3.3-70b-versatile")
    with patch("litellm.completion", side_effect=RuntimeError("network error")):
        with pytest.raises(LLMError) as exc_info:
            client.chat([Message("user", "hi")])
    assert "groq/llama-3.3-70b-versatile" in str(exc_info.value)
    assert "network error" in str(exc_info.value)


def test_complete_single_turn():
    client = LLMClient(model="groq/llama-3.3-70b-versatile")
    with patch("litellm.completion", return_value=_mock_response("pong")) as mock_call:
        result = client.complete("ping")
    assert result == "pong"
    payload = mock_call.call_args.kwargs["messages"]
    assert len(payload) == 1
    assert payload[0]["role"] == "user"
    assert payload[0]["content"] == "ping"


def test_complete_with_system():
    client = LLMClient(model="groq/llama-3.3-70b-versatile")
    with patch("litellm.completion", return_value=_mock_response("ok")) as mock_call:
        client.complete("hello", system="Be brief.")
    payload = mock_call.call_args.kwargs["messages"]
    assert payload[0]["role"] == "system"
    assert payload[0]["content"] == "Be brief."
    assert payload[1]["role"] == "user"


def test_ping_returns_response():
    client = LLMClient(model="groq/llama-3.3-70b-versatile")
    with patch("litellm.completion", return_value=_mock_response("OK")):
        result = client.ping()
    assert result == "OK"


def test_from_env_groq(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LLM_MODEL=groq/llama-3.3-70b-versatile\n"
        "GROQ_API_KEY=gsk_test\n"
    )
    with patch.dict(os.environ, _clean_env(), clear=True):
        client = LLMClient.from_env(env_file)
    assert client.model == "groq/llama-3.3-70b-versatile"
    assert client.temperature == 0.3
    assert client.max_tokens == 1024


def test_from_env_custom_params(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LLM_MODEL=openai/gpt-4o-mini\n"
        "OPENAI_API_KEY=sk_test\n"
        "LLM_TEMPERATURE=0.8\n"
        "LLM_MAX_TOKENS=2048\n"
    )
    with patch.dict(os.environ, _clean_env(), clear=True):
        client = LLMClient.from_env(env_file)
    assert client.temperature == 0.8
    assert client.max_tokens == 2048


def test_from_env_missing_api_key_raises(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_MODEL=groq/llama-3.3-70b-versatile\n")
    with patch.dict(os.environ, _clean_env(), clear=True):
        with pytest.raises(LLMError) as exc_info:
            LLMClient.from_env(env_file)
    assert "GROQ_API_KEY" in str(exc_info.value)


def test_from_env_invalid_temperature_raises(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LLM_MODEL=groq/llama-3.3-70b-versatile\n"
        "GROQ_API_KEY=gsk_test\n"
        "LLM_TEMPERATURE=not_a_float\n"
    )
    with patch.dict(os.environ, _clean_env(), clear=True):
        with pytest.raises(LLMError) as exc_info:
            LLMClient.from_env(env_file)
    assert "invalid config value" in str(exc_info.value)


def test_from_env_ollama_no_key_required(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_MODEL=ollama/llama3.2\n")
    with patch.dict(os.environ, _clean_env(), clear=True):
        client = LLMClient.from_env(env_file)
    assert client.model == "ollama/llama3.2"
