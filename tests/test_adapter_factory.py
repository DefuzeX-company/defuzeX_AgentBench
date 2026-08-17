from pathlib import Path

from agentbench.adapter import (
    AdapterFactory,
    AdapterInvocation,
    UnsupportedAdapterError,
    create_adapter,
)
from agentbench.adapter.langgraph import LangGraphAdapter
from agentbench.harness.registry import AgentRegistration, load_registry


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_factory_creates_registered_langgraph_adapter() -> None:
    registry = load_registry(REPO_ROOT / "resources" / "registry.toml")
    agent = registry.find("langgraph-new-project")

    adapter = create_adapter(agent)

    assert isinstance(adapter, LangGraphAdapter)
    assert not adapter.is_loaded


def test_factory_rejects_unsupported_framework() -> None:
    agent = AgentRegistration(
        agent_id="unknown-agent",
        path=REPO_ROOT,
        enabled=True,
        status="ready",
        framework="unknown",
        source="",
    )

    try:
        create_adapter(agent)
    except UnsupportedAdapterError as exc:
        assert "unknown" in str(exc)
        assert "langgraph" in str(exc)
    else:
        raise AssertionError("Unsupported framework was accepted")


def test_factory_can_register_another_adapter_strategy() -> None:
    class FakeAdapter:
        @property
        def is_loaded(self) -> bool:
            return True

        def load(self) -> "FakeAdapter":
            return self

        def invoke(
            self, value: object, *, run_config: object | None = None
        ) -> AdapterInvocation:
            return AdapterInvocation(output=value, raw_output=value)

        async def ainvoke(
            self, value: object, *, run_config: object | None = None
        ) -> AdapterInvocation:
            return self.invoke(value, run_config=run_config)

        def close(self) -> None:
            pass

    factory = AdapterFactory({"fake": lambda _: FakeAdapter()})
    agent = AgentRegistration(
        agent_id="fake-agent",
        path=REPO_ROOT,
        enabled=True,
        status="ready",
        framework="fake",
        source="",
    )

    adapter = factory.create(agent)

    assert adapter.invoke("hello").output == "hello"
