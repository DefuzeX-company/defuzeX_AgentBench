"""Framework-neutral contracts shared by the harness and all adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


class AgentDescriptor(Protocol):
    """Minimum registration data required to construct an adapter."""

    framework: str
    path: Path


@dataclass(frozen=True)
class AdapterInvocation:
    """Normalized output returned by every adapter."""

    output: object
    raw_output: object


@runtime_checkable
class AgentAdapter(Protocol):
    """Strategy contract used by the benchmark harness."""

    @property
    def is_loaded(self) -> bool:
        ...

    def load(self) -> "AgentAdapter":
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
