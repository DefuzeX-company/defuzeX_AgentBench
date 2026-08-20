"""Tests for API-key driven model configuration."""

import pytest

from src.support_agent.model_factory import (
    ModelConfigurationError,
    clear_model_cache,
    get_model_config,
)


def test_missing_api_key_fails_clearly(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    clear_model_cache()

    with pytest.raises(ModelConfigurationError, match="Missing API key"):
        get_model_config()


def test_openai_compatible_accepts_llm_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    clear_model_cache()

    config = get_model_config()

    assert config.provider == "openai-compatible"
    assert config.api_key == "test-key"
    assert config.base_url == "https://example.test/v1"
