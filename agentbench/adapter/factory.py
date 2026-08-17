"""Create framework adapters from explicit framework registrations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from .base import AgentAdapter, AgentDescriptor
from .langgraph import LangGraphAdapter


AdapterBuilder = Callable[[Path], AgentAdapter]


class AdapterFactoryError(RuntimeError):
    """Base error for adapter registration and construction."""


class UnsupportedAdapterError(AdapterFactoryError):
    """Raised when no adapter is registered for an agent framework."""


class AdapterFactory:
    """Registry-backed factory for framework adapter strategies."""

    def __init__(
        self, builders: Mapping[str, AdapterBuilder] | None = None
    ) -> None:
        self._builders: dict[str, AdapterBuilder] = {}
        for framework, builder in (builders or {}).items():
            self.register(framework, builder)

    def register(
        self,
        framework: str,
        builder: AdapterBuilder,
        *,
        replace: bool = False,
    ) -> None:
        key = _normalize_framework(framework)
        if key in self._builders and not replace:
            raise AdapterFactoryError(f"Adapter is already registered: {key}")
        self._builders[key] = builder

    def create(self, agent: AgentDescriptor) -> AgentAdapter:
        framework = _normalize_framework(agent.framework)
        try:
            builder = self._builders[framework]
        except KeyError as exc:
            supported = ", ".join(self.frameworks()) or "none"
            raise UnsupportedAdapterError(
                f"Unsupported agent framework {agent.framework!r}; supported: {supported}"
            ) from exc

        adapter = builder(agent.path)
        if not isinstance(adapter, AgentAdapter):
            raise AdapterFactoryError(
                f"Builder for {framework!r} did not return an AgentAdapter"
            )
        return adapter

    def frameworks(self) -> tuple[str, ...]:
        return tuple(sorted(self._builders))


def _normalize_framework(framework: str) -> str:
    if not isinstance(framework, str) or not framework.strip():
        raise AdapterFactoryError("Framework must be a non-empty string")
    return framework.strip().lower()


# Right now we only have one adapter
DEFAULT_ADAPTER_FACTORY = AdapterFactory(
    {"langgraph": LangGraphAdapter.from_agent_dir}
)


def create_adapter(
    agent: AgentDescriptor,
    *,
    factory: AdapterFactory = DEFAULT_ADAPTER_FACTORY,
) -> AgentAdapter:
    """Create the registered adapter for one benchmark agent."""

    return factory.create(agent)
