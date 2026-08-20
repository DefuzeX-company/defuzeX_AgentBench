from pathlib import Path

from agentbench.model import ModelBinding, ModelProviderConfig
from agentbench.runtime.contracts import EnvironmentSecretResolver


def test_chat_agent_declares_provider_neutral_model_binding(
    repo_root: Path,
) -> None:
    agent_root = repo_root / "resources" / "agents" / "02-langgraph-chat-agent"
    environ = {"OPENAI_API_KEY": "upstream-secret"}

    binding = ModelBinding.from_agent_dir(
        agent_root,
        secret_resolver=EnvironmentSecretResolver(environ),
        environ=environ,
    )

    assert binding is not None
    assert binding.provider.provider_id == "openai"
    assert binding.provider.protocol == "openai"
    assert binding.upstream_api_key == "upstream-secret"
    assert binding.agent_environment("http://gateway:8080", "run-token") == {
        "OPENAI_BASE_URL": "http://gateway:8080/v1",
        "OPENAI_API_KEY": "run-token",
        "OPENAI_MODEL": "gpt-4.1-mini",
    }


def test_provider_endpoint_can_be_overridden_without_runner_changes(
    repo_root: Path,
) -> None:
    agent_root = repo_root / "resources" / "agents" / "02-langgraph-chat-agent"

    provider = ModelProviderConfig.from_agent_dir(
        agent_root,
        environ={"OPENAI_BASE_URL": "http://host.docker.internal:9000"},
    )

    assert provider is not None
    assert provider.upstream_base_url == "http://host.docker.internal:9000"


def test_email_agent_declares_model_contract(repo_root: Path) -> None:
    agent_root = repo_root / "resources" / "agents" / "03-email-assistant"
    environ = {"OPENAI_API_KEY": "upstream-secret"}

    binding = ModelBinding.from_agent_dir(
        agent_root,
        secret_resolver=EnvironmentSecretResolver(environ),
        environ=environ,
    )

    assert binding is not None
    assert binding.provider.model == "gpt-4.1"
    assert binding.agent_environment("http://gateway:8080", "run-token") == {
        "OPENAI_BASE_URL": "http://gateway:8080/v1",
        "OPENAI_API_KEY": "run-token",
        "OPENAI_MODEL": "gpt-4.1",
    }
