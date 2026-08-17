from pathlib import Path

from agentbench.harness import AgentNotRunningError, AgentRunner, load_registry


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_runner_starts_invokes_and_stops_langgraph_agent() -> None:
    registry = load_registry(REPO_ROOT / "resources" / "registry.toml")
    registration = registry.find("langgraph-new-project")

    running = AgentRunner().start(registration)

    assert running.agent_id == "langgraph-new-project"
    assert running.adapter_name == "LangGraphAdapter"
    assert running.is_running
    assert running.invoke("DEFUZEX_AGENT_READY").output == "DEFUZEX_AGENT_READY"

    running.stop()
    assert not running.is_running

    try:
        running.invoke("after stop")
    except AgentNotRunningError:
        pass
    else:
        raise AssertionError("Stopped agent accepted an invocation")


def test_running_agent_context_manager_stops_agent() -> None:
    registry = load_registry(REPO_ROOT / "resources" / "registry.toml")
    registration = registry.find("langgraph-new-project")

    with AgentRunner().start(registration) as running:
        assert running.is_running

    assert not running.is_running
