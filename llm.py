# llm.py
"""LLM client using LiteLLM — unified interface for multiple providers.

LiteLLM translates calls to any provider (Groq, OpenAI, Anthropic, etc.)
using the same API. Switching providers is a one-line .env change.

Current default: Groq (fast, free tier available)
  Model format : groq/<model_name>
  Auth         : GROQ_API_KEY in .env (picked up automatically by LiteLLM)

Other supported providers (just change LLM_MODEL in .env):
  OpenAI    : openai/gpt-4o-mini
  Anthropic : anthropic/claude-haiku-4-5-20251001
  Ollama    : ollama/llama3.2  (local, no key needed)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import litellm
from dotenv import load_dotenv

from errors import LLMError

# Suppress LiteLLM's verbose logging by default
litellm.suppress_debug_info = True


@dataclass
class Message:
    """A single chat message."""

    role: str    # "system", "user", or "assistant"
    content: str


@dataclass
class LLMClient:
    """LiteLLM wrapper for Nina.

    All methods raise :class:`errors.LLMError` on failure so callers
    don't need to import litellm or handle provider-specific exceptions.
    """

    model: str
    temperature: float = 0.3
    max_tokens: int = 1024

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    def chat(self, messages: list[Message]) -> str:
        """Send a conversation and return the assistant's reply.

        Args:
            messages: Ordered list of system/user/assistant messages.

        Returns:
            The text content of the model's response.

        Raises:
            LLMError: On any provider or network error.
        """
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
        """Single-turn completion — convenience wrapper around :meth:`chat`.

        Args:
            prompt: The user message.
            system: Optional system prompt to prepend.

        Returns:
            The model's response text.
        """
        messages: list[Message] = []
        if system:
            messages.append(Message("system", system))
        messages.append(Message("user", prompt))
        return self.chat(messages)

    def ping(self) -> str:
        """Send a minimal request to verify connectivity and auth.

        Returns:
            The model's short response (should be "OK").
        """
        return self.complete(
            'Respond with exactly one word: "OK"',
            system="You are a minimal connectivity test. Reply with exactly: OK",
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "LLMClient":
        """Create from environment variables (loads .env automatically).

        Required .env variables::

            LLM_MODEL=groq/llama-3.3-70b-versatile
            GROQ_API_KEY=gsk_...

        Optional::

            LLM_TEMPERATURE=0.3
            LLM_MAX_TOKENS=1024

        Raises:
            LLMError: If required config is missing.
        """
        load_dotenv(env_file)

        model = os.environ.get("LLM_MODEL", "groq/llama-3.3-70b-versatile")
        provider = model.split("/")[0] if "/" in model else model

        # Validate that the expected API key is present.
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
