"""Load, invoke, and stop registered benchmark agents."""

from __future__ import annotations

from agentbench.adapter import (
    DEFAULT_ADAPTER_FACTORY,
    AdapterFactory,
)
from agentbench.runtime import DEFAULT_RUNTIME_FACTORY, RuntimeFactory

from ..errors import AgentStartError
from ..registry import AgentRegistration
from .running_agent import RunningAgent


class AgentRunner:
    """Create an adapter and load one registered agent."""

    def __init__(
        self,
        *,
        adapter_factory: AdapterFactory = DEFAULT_ADAPTER_FACTORY,
        runtime_factory: RuntimeFactory = DEFAULT_RUNTIME_FACTORY,
    ) -> None:
        self._adapter_factory = adapter_factory
        self._runtime_factory = runtime_factory

    def start(self, agent: AgentRegistration) -> RunningAgent:
        adapter = self._runtime_factory.create_adapter(
            agent,
            adapter_factory=self._adapter_factory,
        )
        try:
            adapter.load()
        except Exception as exc:
            adapter.close()
            raise AgentStartError(f"Failed to start agent {agent.agent_id!r}") from exc
        return RunningAgent(registration=agent, adapter=adapter)
