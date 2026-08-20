from pathlib import Path

import pytest

from agentbench.harness.registry import load_registry

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("agent_id", "directory", "case_count"),
    [
        ("langgraph-new-project", "01-langgraph-new-project", 3),
        ("langgraph-chat-agent", "02-langgraph-chat-agent", 5),
        ("email-assistant", "03-email-assistant", 2),
    ],
)
def test_registry_resolves_enabled_agents(
    agent_id: str, directory: str, case_count: int
) -> None:
    registry = load_registry(REPO_ROOT / "resources" / "registry.toml")

    agent = registry.find(agent_id)

    assert agent.agent_id == agent_id
    assert agent.framework == "langgraph"
    assert agent.status == "ready"
    assert agent.case_count == case_count
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


def test_registry_defaults_case_count_to_one(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path)

    agent = load_registry(registry_path).find("test-agent")

    assert agent.case_count == 1


@pytest.mark.parametrize("case_value", ["0", "-1", "true", '"2"', "1.5"])
def test_registry_rejects_invalid_case_count(
    tmp_path: Path, case_value: str
) -> None:
    registry_path = _write_registry(tmp_path, case_value=case_value)

    with pytest.raises(ValueError, match="positive integer: case"):
        load_registry(registry_path)


def _write_registry(tmp_path: Path, *, case_value: str | None = None) -> Path:
    resources = tmp_path / "resources"
    agent_path = resources / "agents" / "test-agent"
    requirement_path = resources / "requirements" / "test-agent.md"
    agent_path.mkdir(parents=True)
    requirement_path.parent.mkdir(parents=True)
    (agent_path / "agent.toml").write_text(
        'agent_id = "test-agent"\n', encoding="utf-8"
    )
    requirement_path.write_text("# Test requirement\n", encoding="utf-8")
    case_line = "" if case_value is None else f"case = {case_value}\n"
    registry_path = resources / "registry.toml"
    registry_path.write_text(
        'schema_version = "defuzex-bench.registry.v1"\n\n'
        "[[agents]]\n"
        'agent_id = "test-agent"\n'
        'path = "resources/agents/test-agent"\n'
        'framework = "langgraph"\n'
        f"{case_line}",
        encoding="utf-8",
    )
    return registry_path
