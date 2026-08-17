from pathlib import Path

from agentbench.harness.registry import load_registry


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_find_langgraph_new_project() -> None:
    """Check registry can find the starter agent."""
    registry = load_registry(REPO_ROOT / "resources" / "registry.toml")

    agent = registry.find("langgraph-new-project")

    assert agent.agent_id == "langgraph-new-project"
    assert agent.framework == "langgraph"
    assert agent.path == REPO_ROOT / "resources" / "agents" / "langgraph-new-project"
    assert agent.path.joinpath("agent.toml").is_file()
