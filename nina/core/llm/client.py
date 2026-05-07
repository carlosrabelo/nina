# nina/llm/client.py
"""LLM client using LiteLLM — unified interface for multiple providers."""

import os
from dataclasses import dataclass
from pathlib import Path

import litellm
from dotenv import load_dotenv

from nina.errors import LLMError

# Suppress LiteLLM's verbose logging by default
litellm.suppress_debug_info = True


@dataclass
class Message:
    """A single chat message."""

    role: str    # "system", "user", or "assistant"
    content: str


@dataclass
class LLMClient:
    """LiteLLM wrapper for Nina."""

    model: str
    temperature: float = 0.3
    max_tokens: int = 1024

    def chat(self, messages: list[Message]) -> str:
        """Send a conversation and return the assistant's reply."""
        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return str(response.choices[0].message.content)
        except Exception as e:
            raise LLMError(self.model, str(e)) from e

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Single-turn completion — convenience wrapper around chat."""
        messages: list[Message] = []
        if system:
            messages.append(Message("system", system))
        messages.append(Message("user", prompt))
        return self.chat(messages)

    def ping(self) -> str:
        """Send a minimal request to verify connectivity and auth."""
        return self.complete(
            'Respond with exactly one word: "OK"',
            system="You are a minimal connectivity test. Reply with exactly: OK",
        )

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "LLMClient":
        """Create from environment variables (loads .env automatically)."""
        load_dotenv(env_file)

        model = os.environ.get("LLM_MODEL", "groq/llama-3.3-70b-versatile")
        provider = model.split("/")[0] if "/" in model else model

        key_map = {
            "groq": "GROQ_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        if provider in key_map:
            key_name = key_map[provider]
            if not os.environ.get(key_name):
                raise LLMError(
                    model,
                    f"{key_name} not set in .env\n"
                    f"Get your key at the {provider} dashboard and add it to .env.",
                )

        try:
            temperature = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
            max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "1024"))
        except ValueError as e:
            raise LLMError(model, f"invalid config value: {e}") from e

        return cls(model=model, temperature=temperature, max_tokens=max_tokens)
