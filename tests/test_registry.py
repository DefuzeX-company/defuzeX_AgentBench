from pathlib import Path

import pytest

from agentbench.harness.registry import load_registry

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("agent_id", "directory"),
    [
        ("langgraph-new-project", "01-langgraph-new-project"),
        ("langgraph-chat-agent", "02-langgraph-chat-agent"),
        ("email-assistant", "03-email-assistant"),
    ],
)
def test_registry_resolves_enabled_agents(agent_id: str, directory: str) -> None:
    registry = load_registry(REPO_ROOT / "resources" / "registry.toml")

    agent = registry.find(agent_id)

    assert agent.agent_id == agent_id
    assert agent.framework == "langgraph"
    assert agent.status == "ready"
    assert agent.path == REPO_ROOT / "resources" / "agents" / directory
    assert agent.path.joinpath("agent.toml").is_file()
    assert agent.requirement_path == (
        REPO_ROOT / "resources" / "requirements" / f"{agent_id}.md"
    )


def test_every_enabled_agent_has_an_sdk_requirement() -> None:
    registry = load_registry(REPO_ROOT / "resources" / "registry.toml")

    for agent in registry.enabled():
        requirement = REPO_ROOT / "resources" / "requirements" / f"{agent.agent_id}.md"
        assert requirement.is_file(), f"Missing SDK requirement: {requirement}"
        assert agent.requirement_path == requirement
