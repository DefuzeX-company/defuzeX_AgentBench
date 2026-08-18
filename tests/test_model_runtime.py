import json
import sys
from pathlib import Path
from types import MappingProxyType


REPO_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_SERVICE_SRC = REPO_ROOT / "services" / "model-gateway" / "src"
sys.path.insert(0, str(GATEWAY_SERVICE_SRC))

from agentbench.adapter import DEFAULT_ADAPTER_FACTORY
from agentbench.model import ModelBinding, ModelProviderConfig
from agentbench.runtime.agentcontainer import AgentContainerConfig, ContainerAgentAdapter
from agentbench.runtime.contracts import EnvironmentSecretResolver
from agentbench.runtime.docker import DockerPolicy
from agentbench.runtime.docker.session import _json_compatible
from agentbench.runtime.factory import RuntimeFactory
from agentbench.harness import load_registry
from defuzex_model_gateway.protocols import GatewayAuthenticationError, get_protocol


CHAT_AGENT = REPO_ROOT / "resources" / "agents" / "02-langgraph-chat-agent"
EMAIL_AGENT = REPO_ROOT / "resources" / "agents" / "03-email-assistant"


def test_chat_agent_declares_provider_neutral_model_binding() -> None:
    environ = {"OPENAI_API_KEY": "upstream-secret"}
    binding = ModelBinding.from_agent_dir(
        CHAT_AGENT,
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


def test_provider_endpoint_can_be_overridden_without_runner_changes() -> None:
    provider = ModelProviderConfig.from_agent_dir(
        CHAT_AGENT,
        environ={"OPENAI_BASE_URL": "http://host.docker.internal:9000"},
    )

    assert provider is not None
    assert provider.upstream_base_url == "http://host.docker.internal:9000"


def test_openai_protocol_replaces_the_run_token_with_upstream_key() -> None:
    protocol = get_protocol("openai")
    path, headers = protocol.authorize(
        "/v1/chat/completions",
        {"Authorization": "Bearer run-token", "Content-Type": "application/json"},
        gateway_token="run-token",
        upstream_api_key="provider-secret",
    )

    assert path == "/v1/chat/completions"
    assert headers["Authorization"] == "Bearer provider-secret"
    assert headers["Content-Type"] == "application/json"


def test_model_protocol_rejects_an_invalid_run_token() -> None:
    try:
        get_protocol("openai").authorize(
            "/v1/chat/completions",
            {"Authorization": "Bearer wrong"},
            gateway_token="run-token",
            upstream_api_key="provider-secret",
        )
    except GatewayAuthenticationError:
        pass
    else:
        raise AssertionError("Gateway accepted an invalid per-run token")


def test_chat_agent_container_configuration_is_machine_driven() -> None:
    config = AgentContainerConfig.from_agent_dir(
        CHAT_AGENT,
        secret_resolver=EnvironmentSecretResolver({}),
        environ={},
    )

    assert config.argv == ("python", "-m", "chat_agent.worker")
    assert config.timeout_sec == 60
    assert config.environment == {}


def test_email_agent_declares_container_and_model_contracts() -> None:
    environ = {"OPENAI_API_KEY": "upstream-secret"}
    resolver = EnvironmentSecretResolver(environ)

    config = AgentContainerConfig.from_agent_dir(
        EMAIL_AGENT,
        secret_resolver=resolver,
        environ=environ,
    )
    binding = ModelBinding.from_agent_dir(
        EMAIL_AGENT,
        secret_resolver=resolver,
        environ=environ,
    )

    assert config.argv == ("python", "-m", "email_assistant.worker")
    assert config.timeout_sec == 120
    assert binding is not None
    assert binding.provider.model == "gpt-4.1"
    assert binding.agent_environment("http://gateway:8080", "run-token") == {
        "OPENAI_BASE_URL": "http://gateway:8080/v1",
        "OPENAI_API_KEY": "run-token",
        "OPENAI_MODEL": "gpt-4.1",
    }


def test_runtime_factory_selects_container_without_starting_docker() -> None:
    class NeverStartedRuntime:
        def start(self, agent):  # type: ignore[no-untyped-def]
            raise AssertionError("Runtime should remain lazy")

    registry = load_registry(REPO_ROOT / "resources" / "registry.toml")
    registration = registry.find("langgraph-chat-agent")
    factory = RuntimeFactory(docker_builder=NeverStartedRuntime)

    adapter = factory.create_adapter(
        registration,
        adapter_factory=DEFAULT_ADAPTER_FACTORY,
    )

    assert isinstance(adapter, ContainerAgentAdapter)
    assert not adapter.is_loaded


def test_docker_policy_contains_required_isolation_controls() -> None:
    arguments = DockerPolicy().run_arguments()

    assert "--read-only" in arguments
    assert "--cap-drop=ALL" in arguments
    assert "--security-opt=no-new-privileges" in arguments
    assert any(value.startswith("--memory=") for value in arguments)
    assert any(value.startswith("--cpus=") for value in arguments)
    assert any(value.startswith("--pids-limit=") for value in arguments)


def test_docker_transport_serializes_frozen_sdk_payloads() -> None:
    payload = MappingProxyType(
        {
            "email_input": MappingProxyType({"subject": "Hello"}),
        }
    )

    encoded = json.dumps(payload, default=_json_compatible)

    assert json.loads(encoded) == {"email_input": {"subject": "Hello"}}
