import pytest

from agentbench.harness import (
    AgentNotRunningError,
    AgentRegistration,
    AgentRunner,
)


def test_runner_starts_invokes_and_stops_langgraph_agent(
    starter_agent: AgentRegistration,
) -> None:
    running = AgentRunner().start(starter_agent)

    assert running.agent_id == "langgraph-new-project"
    assert running.adapter_name == "LangGraphAdapter"
    assert running.is_running
    assert running.invoke("DEFUZEX_AGENT_READY").output == "DEFUZEX_AGENT_READY"

    running.stop()
    assert not running.is_running

    with pytest.raises(AgentNotRunningError):
        running.invoke("after stop")


def test_running_agent_context_manager_stops_agent(
    starter_agent: AgentRegistration,
) -> None:
    with AgentRunner().start(starter_agent) as running:
        assert running.is_running

    assert not running.is_running
