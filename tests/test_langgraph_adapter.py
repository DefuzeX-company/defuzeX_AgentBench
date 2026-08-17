from pathlib import Path

from agentbench.adapter.langgraph import LangGraphAdapter, LangGraphAdapterConfig


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = REPO_ROOT / "resources" / "agents" / "langgraph-new-project"


def test_config_resolves_official_langgraph_entrypoint() -> None:
    """Check adapter config reads langgraph.json."""
    config = LangGraphAdapterConfig.from_agent_dir(AGENT_ROOT)

    assert config.graph_id == "agent"
    assert config.entrypoint == "./src/agent/graph.py:graph"
    assert config.input_key == "prompt"
    assert config.output_key == "response"


def test_adapter_loads_and_invokes_graph() -> None:
    """Check adapter can run the starter graph."""
    adapter = LangGraphAdapter.from_agent_dir(AGENT_ROOT)

    invocation = adapter.invoke("DEFUZEX_AGENT_READY")

    assert adapter.is_loaded
    assert invocation.output == "DEFUZEX_AGENT_READY"
    assert invocation.raw_output == {
        "prompt": "DEFUZEX_AGENT_READY",
        "response": "DEFUZEX_AGENT_READY",
    }
