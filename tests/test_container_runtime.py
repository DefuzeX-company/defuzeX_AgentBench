from pathlib import Path

from agentbench.adapter import DEFAULT_ADAPTER_FACTORY
from agentbench.harness import AgentRegistry
from agentbench.runtime.agentcontainer import (
    AgentContainerConfig,
    ContainerAgentAdapter,
)
from agentbench.runtime.contracts import EnvironmentSecretResolver
from agentbench.runtime.factory import RuntimeFactory


def test_chat_agent_container_configuration_is_machine_driven(
    repo_root: Path,
) -> None:
    agent_root = repo_root / "resources" / "agents" / "02-langgraph-chat-agent"

    config = AgentContainerConfig.from_agent_dir(
        agent_root,
        secret_resolver=EnvironmentSecretResolver({}),
        environ={},
    )

    assert config.argv == ("python", "-m", "chat_agent.worker")
    assert config.timeout_sec == 60
    assert config.environment == {}


def test_email_agent_declares_container_contract(repo_root: Path) -> None:
    agent_root = repo_root / "resources" / "agents" / "03-email-assistant"
    environ = {"OPENAI_API_KEY": "upstream-secret"}

    config = AgentContainerConfig.from_agent_dir(
        agent_root,
        secret_resolver=EnvironmentSecretResolver(environ),
        environ=environ,
    )

    assert config.argv == ("python", "-m", "email_assistant.worker")
    assert config.timeout_sec == 120


def test_runtime_factory_selects_container_without_starting_docker(
    registry: AgentRegistry,
) -> None:
    class NeverStartedRuntime:
        def start(self, agent):  # type: ignore[no-untyped-def]
            raise AssertionError("Runtime should remain lazy")

    registration = registry.find("langgraph-chat-agent")
    factory = RuntimeFactory(docker_builder=NeverStartedRuntime)

    adapter = factory.create_adapter(
        registration,
        adapter_factory=DEFAULT_ADAPTER_FACTORY,
    )

    assert isinstance(adapter, ContainerAgentAdapter)
    assert not adapter.is_loaded
