from dataclasses import dataclass
from pathlib import Path

from agentbench.harness import (
    BenchmarkProgress,
    BenchmarkResult,
    ProviderSelectionError,
    SuiteConfigurationError,
    SuiteRunner,
    load_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class FakeReport:
    status: str
    confidence: object = 1.0
    issues: tuple[object, ...] = ()
    evidence_gaps: tuple[object, ...] = ()


def benchmark_result(agent_id: str, *, status: str = "pass") -> BenchmarkResult:
    return BenchmarkResult(
        agent_id=agent_id,
        adapter_name="FakeAdapter",
        run_id=f"run_{agent_id}",
        run_state="report_ready",
        report=FakeReport(status),
        steps=(),
        history_count=1,
        provider_mode="official",
    )


class FakeBenchmarkRunner:
    def __init__(
        self,
        outcomes: dict[str, object],
        *,
        validation_error: Exception | None = None,
    ) -> None:
        self.outcomes = outcomes
        self.validation_error = validation_error
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.validation_calls: list[str] = []

    def validate_defuzex(self, registration, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        self.validation_calls.append(registration.agent_id)
        if self.validation_error is not None:
            raise self.validation_error
        return "official"

    def run_defuzex(self, registration, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append((registration.agent_id, kwargs))
        outcome = self.outcomes[registration.agent_id]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def registered_agents():  # type: ignore[no-untyped-def]
    return load_registry(REPO_ROOT / "resources" / "registry.toml").enabled()


def test_suite_runner_runs_every_agent_and_aggregates_results() -> None:
    agents = registered_agents()
    fake = FakeBenchmarkRunner(
        {agent.agent_id: benchmark_result(agent.agent_id) for agent in agents}
    )
    started: list[str] = []
    completed: list[str] = []
    events: list[BenchmarkProgress] = []

    result = SuiteRunner(benchmark_runner=fake).run_defuzex(  # type: ignore[arg-type]
        agents,
        api_key="dfx_test",
        allow_local=True,
        track_files=False,
        on_agent_start=lambda agent, index, total: started.append(
            f"{index}/{total}:{agent.agent_id}"
        ),
        on_agent_complete=lambda item: completed.append(item.agent_id),
        on_progress=events.append,
    )

    expected_ids = [agent.agent_id for agent in agents]
    assert [agent_id for agent_id, _ in fake.calls] == expected_ids
    assert started == [
        f"{index}/{len(agents)}:{agent_id}"
        for index, agent_id in enumerate(expected_ids, start=1)
    ]
    assert completed == expected_ids
    assert fake.validation_calls == [agents[0].agent_id]
    assert [(event.stage, event.status) for event in events[:2]] == [
        ("sdk_check", "started"),
        ("sdk_check", "succeeded"),
    ]
    assert result.passed
    assert result.selected_count == len(agents)
    assert result.attempted_count == len(agents)
    assert result.passed_count == len(agents)
    assert result.failed_count == 0
    assert result.skipped_count == 0
    for _, kwargs in fake.calls:
        assert kwargs["api_key"] == "dfx_test"
        assert kwargs["allow_local"] is True
        assert kwargs["track_files"] is False


def test_suite_runner_records_agent_error_and_continues() -> None:
    agents = registered_agents()
    outcomes: dict[str, object] = {
        agent.agent_id: benchmark_result(agent.agent_id) for agent in agents
    }
    outcomes[agents[1].agent_id] = RuntimeError("container failed")
    fake = FakeBenchmarkRunner(outcomes)

    result = SuiteRunner(benchmark_runner=fake).run_defuzex(agents)  # type: ignore[arg-type]

    assert result.attempted_count == len(agents)
    assert result.passed_count == len(agents) - 1
    assert result.failed_count == 1
    assert not result.passed
    failed = result.items[1]
    assert failed.error_type == "RuntimeError"
    assert failed.error_message == "container failed"


def test_suite_runner_can_stop_after_first_failed_benchmark() -> None:
    agents = registered_agents()
    outcomes = {
        agents[0].agent_id: benchmark_result(agents[0].agent_id, status="fail"),
        agents[1].agent_id: benchmark_result(agents[1].agent_id),
        agents[2].agent_id: benchmark_result(agents[2].agent_id),
    }
    fake = FakeBenchmarkRunner(outcomes)

    result = SuiteRunner(benchmark_runner=fake).run_defuzex(  # type: ignore[arg-type]
        agents,
        continue_on_error=False,
    )

    assert result.attempted_count == 1
    assert result.failed_count == 1
    assert result.skipped_count == len(agents) - 1
    assert not result.passed


def test_suite_runner_propagates_shared_provider_configuration_error() -> None:
    agents = registered_agents()
    events: list[BenchmarkProgress] = []
    fake = FakeBenchmarkRunner(
        {agent.agent_id: benchmark_result(agent.agent_id) for agent in agents},
        validation_error=ProviderSelectionError("missing provider"),
    )

    try:
        SuiteRunner(benchmark_runner=fake).run_defuzex(  # type: ignore[arg-type]
            agents,
            on_progress=events.append,
        )
    except SuiteConfigurationError as exc:
        assert str(exc) == "missing provider"
    else:
        raise AssertionError("SuiteRunner swallowed a shared configuration error")

    assert len(fake.calls) == 0
    assert len(fake.validation_calls) == 1
    assert [(event.stage, event.status) for event in events] == [
        ("sdk_check", "started"),
        ("sdk_check", "failed"),
    ]
    assert events[-1].detail == "ProviderSelectionError: missing provider"


def test_suite_runner_rejects_an_empty_selection() -> None:
    try:
        SuiteRunner().run_defuzex(())
    except ValueError as exc:
        assert "at least one Agent" in str(exc)
    else:
        raise AssertionError("SuiteRunner accepted an empty selection")
