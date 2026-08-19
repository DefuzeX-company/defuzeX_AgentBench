from dataclasses import dataclass

from agentbench.adapter import AdapterInvocation
from agentbench.harness import (
    BenchmarkResult,
    BenchmarkStepResult,
    BenchmarkSuiteResult,
    SuiteAgentResult,
)


@dataclass(frozen=True)
class FakeReport:
    status: str = "pass"
    confidence: object = 1.0
    issues: tuple[object, ...] = ()
    evidence_gaps: tuple[object, ...] = ()


def benchmark_result(
    agent_id: str,
    *,
    status: str = "pass",
    with_step: bool = False,
) -> BenchmarkResult:
    steps: tuple[BenchmarkStepResult, ...] = ()
    if with_step:
        steps = (
            BenchmarkStepResult(
                input_id=f"input_{agent_id}",
                payload={"prompt": f"Prompt for {agent_id}"},
                invocation=AdapterInvocation(
                    output={"answer": "ok"},
                    raw_output={
                        "node": "final",
                        "messages": [f"trace for {agent_id}"],
                    },
                ),
            ),
        )

    return BenchmarkResult(
        agent_id=agent_id,
        adapter_name="FakeAdapter",
        run_id=f"run_{agent_id}",
        run_state="report_ready",
        report=FakeReport(status),
        steps=steps,
        history_count=1,
        provider_mode="official",
    )


def suite_result(*agent_ids: str) -> BenchmarkSuiteResult:
    return BenchmarkSuiteResult(
        suite_id="suite_test",
        selected_agent_ids=agent_ids,
        items=tuple(
            SuiteAgentResult(
                agent_id=agent_id,
                benchmarks=(benchmark_result(agent_id, with_step=True),),
            )
            for agent_id in agent_ids
        ),
    )
