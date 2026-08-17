"""Framework-neutral results produced by the benchmark harness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agentbench.adapter import AdapterInvocation


class SDKReport(Protocol):
    """Public SDK report fields consumed by AgentBench."""

    status: str
    confidence: object
    issues: tuple[object, ...]
    evidence_gaps: tuple[object, ...]


@dataclass(frozen=True)
class BenchmarkStepResult:
    """One SDK Input and the corresponding Agent invocation."""

    input_id: str
    payload: object
    invocation: AdapterInvocation


@dataclass(frozen=True)
class BenchmarkResult:
    """Completed Harness execution for one registered Agent."""

    agent_id: str
    adapter_name: str
    run_id: str
    run_state: str
    report: SDKReport | None
    steps: tuple[BenchmarkStepResult, ...]
    history_count: int
    provider_mode: str | None = None

    @property
    def passed(self) -> bool:
        return self.report is not None and self.report.status == "pass"
