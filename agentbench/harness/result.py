"""Framework-neutral results produced by the benchmark harness."""

from __future__ import annotations

from dataclasses import dataclass

from agentbench.adapter import AdapterInvocation

from .protocols import SDKReport


@dataclass(frozen=True)
class BenchmarkStepResult:
    """One SDK Input and the corresponding Agent invocation."""

    input_id: str
    payload: object
    invocation: AdapterInvocation


@dataclass(frozen=True)
class BenchmarkStepFailure:
    """One SDK Input that failed before the full step completed."""

    input_id: str
    payload: object
    error_type: str
    error_message: str
    output: object | None = None
    raw_output: object | None = None


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


@dataclass(frozen=True)
class SuiteAgentResult:
    """Outcome for one selected Agent in a benchmark suite."""

    agent_id: str
    benchmark: BenchmarkResult | None = None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        has_benchmark = self.benchmark is not None
        has_error = self.error_type is not None
        if has_benchmark == has_error:
            raise ValueError(
                "Suite Agent result requires exactly one benchmark or error"
            )
        if has_error and self.error_message is None:
            raise ValueError("Suite Agent error requires an error message")
        if self.benchmark is not None and self.benchmark.agent_id != self.agent_id:
            raise ValueError("Suite Agent ID does not match its benchmark result")

    @property
    def passed(self) -> bool:
        return self.benchmark is not None and self.benchmark.passed


@dataclass(frozen=True)
class BenchmarkSuiteResult:
    """Aggregate result for a selected set of benchmark Agents."""

    selected_agent_ids: tuple[str, ...]
    items: tuple[SuiteAgentResult, ...]

    def __post_init__(self) -> None:
        if not self.selected_agent_ids:
            raise ValueError("A benchmark suite result requires selected Agents")
        attempted_ids = tuple(item.agent_id for item in self.items)
        if attempted_ids != self.selected_agent_ids[: len(attempted_ids)]:
            raise ValueError("Suite result items must follow the selected Agent order")

    @property
    def selected_count(self) -> int:
        return len(self.selected_agent_ids)

    @property
    def attempted_count(self) -> int:
        return len(self.items)

    @property
    def passed_count(self) -> int:
        return sum(item.passed for item in self.items)

    @property
    def failed_count(self) -> int:
        return self.attempted_count - self.passed_count

    @property
    def skipped_count(self) -> int:
        return self.selected_count - self.attempted_count

    @property
    def passed(self) -> bool:
        return self.skipped_count == 0 and self.failed_count == 0
