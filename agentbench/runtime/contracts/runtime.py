"""Framework-neutral contracts for isolated agent runtimes."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from agentbench.adapter import AdapterInvocation, AgentDescriptor


@runtime_checkable
class RuntimeSession(Protocol):
    @property
    def is_running(self) -> bool:
        ...

    def invoke(
        self, value: object, *, run_config: object | None = None
    ) -> AdapterInvocation:
        ...

    async def ainvoke(
        self, value: object, *, run_config: object | None = None
    ) -> AdapterInvocation:
        ...

    def close(self) -> None:
        ...


@runtime_checkable
class AgentRuntime(Protocol):
    def start(self, agent: AgentDescriptor) -> RuntimeSession:
        ...
