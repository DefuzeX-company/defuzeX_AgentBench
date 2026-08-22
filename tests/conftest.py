from pathlib import Path

import pytest

from agentbench.harness import AgentRegistration, AgentRegistry, load_registry


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def registry(repo_root: Path) -> AgentRegistry:
    return load_registry(repo_root / "resources" / "registry.toml")


@pytest.fixture(scope="session")
def starter_agent(registry: AgentRegistry) -> AgentRegistration:
    return registry.find("langgraph-new-project", enabled_only=False)


@pytest.fixture(scope="session")
def enabled_agents(registry: AgentRegistry) -> tuple[AgentRegistration, ...]:
    return registry.enabled()


@pytest.fixture(scope="session")
def ready_agents(registry: AgentRegistry) -> tuple[AgentRegistration, ...]:
    return registry.ready()
