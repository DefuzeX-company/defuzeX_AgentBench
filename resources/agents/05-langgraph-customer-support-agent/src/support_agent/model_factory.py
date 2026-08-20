"""API-key driven chat model factory for the support agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


class ModelConfigurationError(RuntimeError):
    """Raised when the selected LLM provider is not configured."""


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    api_key: str
    base_url: str | None
    temperature: float
    timeout: float


def _read_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ModelConfigurationError(f"{name} must be a number, got {value!r}") from exc


def get_model_config() -> ModelConfig:
    """Read the selected provider and credentials from the environment."""
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()

    if provider not in {"openai", "openai-compatible"}:
        raise ModelConfigurationError(
            "Unsupported LLM_PROVIDER "
            f"{provider!r}. Supported providers: openai, openai-compatible."
        )

    if provider == "openai-compatible":
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    else:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise ModelConfigurationError(
            "Missing API key for LLM_PROVIDER="
            f"{provider}. Set OPENAI_API_KEY or LLM_API_KEY before running the agent."
        )

    return ModelConfig(
        provider=provider,
        model=os.getenv("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        api_key=api_key,
        base_url=(os.getenv("LLM_BASE_URL") or None),
        temperature=_read_float_env("LLM_TEMPERATURE", 0.0),
        timeout=_read_float_env("LLM_TIMEOUT_SECONDS", 60.0),
    )


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """Create the configured chat model without any local-model fallback."""
    config = get_model_config()

    kwargs: dict[str, object] = {
        "model": config.model,
        "api_key": config.api_key,
        "temperature": config.temperature,
        "timeout": config.timeout,
    }
    if config.base_url:
        kwargs["base_url"] = config.base_url

    return ChatOpenAI(**kwargs)


def clear_model_cache() -> None:
    """Clear cached model instances for tests that change environment variables."""
    get_chat_model.cache_clear()
