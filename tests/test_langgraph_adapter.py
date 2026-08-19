from pathlib import Path

from agentbench.adapter.langgraph import LangGraphAdapter, LangGraphAdapterConfig


def test_config_resolves_official_langgraph_entrypoint(repo_root: Path) -> None:
    """Check adapter config reads langgraph.json."""
    agent_root = repo_root / "resources" / "agents" / "01-langgraph-new-project"
    config = LangGraphAdapterConfig.from_agent_dir(agent_root)

    assert config.graph_id == "agent"
    assert config.entrypoint == "./src/agent/graph.py:graph"
    assert config.input_key == "prompt"
    assert config.output_key == "response"


def test_adapter_loads_and_invokes_graph(repo_root: Path) -> None:
    """Check adapter can run the starter graph."""
    agent_root = repo_root / "resources" / "agents" / "01-langgraph-new-project"
    adapter = LangGraphAdapter.from_agent_dir(agent_root)

    invocation = adapter.invoke("DEFUZEX_AGENT_READY")

    assert adapter.is_loaded
    assert invocation.output == "DEFUZEX_AGENT_READY"
    assert invocation.raw_output == {
        "prompt": "DEFUZEX_AGENT_READY",
        "response": "DEFUZEX_AGENT_READY",
    }
