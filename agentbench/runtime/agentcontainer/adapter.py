"""AgentAdapter implementation backed by an isolated runtime session."""

from __future__ import annotations

import asyncio

from agentbench.adapter import AdapterInvocation, AgentDescriptor
from agentbench.runtime.contracts import AgentRuntime, RuntimeSession


class ContainerAgentAdapter:
    def __init__(self, agent: AgentDescriptor, runtime: AgentRuntime) -> None:
        self._agent = agent
        self._runtime = runtime
        self._session: RuntimeSession | None = None

    @property
    def is_loaded(self) -> bool:
        return self._session is not None and self._session.is_running

    def load(self) -> "ContainerAgentAdapter":
        if self._session is None:
            self._session = self._runtime.start(self._agent)
        return self

    def invoke(
        self, value: object, *, run_config: object | None = None
    ) -> AdapterInvocation:
        return self._require_session().invoke(value, run_config=run_config)

    async def ainvoke(
        self, value: object, *, run_config: object | None = None
    ) -> AdapterInvocation:
        session = self._require_session()
        async_invoke = getattr(session, "ainvoke", None)
        if callable(async_invoke):
            return await async_invoke(value, run_config=run_config)
        return await asyncio.to_thread(session.invoke, value, run_config=run_config)

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None

    def _require_session(self) -> RuntimeSession:
        if self._session is None:
            self.load()
        if self._session is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Container runtime did not create a session")
        return self._session
