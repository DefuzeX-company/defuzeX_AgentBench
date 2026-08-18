from dataclasses import dataclass

from agentbench.cli.main import (
    DEFAULT_REGISTRY_PATH,
    confirm_agents,
    main,
)
from agentbench.cli.logo import DEFUZE_LOGO
from agentbench.cli.constants import (
    AGENT_REVEAL_DELAY_SECONDS,
    ANSI_GREEN,
    ANSI_RED,
    ANSI_RESET,
    LOGO_PAUSE_SECONDS,
)
from agentbench.harness import (
    BenchmarkProgress,
    BenchmarkResult,
    BenchmarkSuiteResult,
    ProviderSelectionError,
    SuiteAgentResult,
    load_registry,
)


@dataclass(frozen=True)
class FakeReport:
    status: str = "pass"
    confidence: object = 1.0
    issues: tuple[object, ...] = ()
    evidence_gaps: tuple[object, ...] = ()


class FakeSuiteRunner:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[object, dict[str, object]]] = []

    def run_defuzex(self, agents, **kwargs):  # type: ignore[no-untyped-def]
        selected = tuple(agents)
        self.calls.append((selected, kwargs))
        if self.error is not None:
            raise self.error

        progress = kwargs.get("on_progress")
        if callable(progress):
            progress(BenchmarkProgress("sdk_check", "started"))
            progress(
                BenchmarkProgress(
                    "sdk_check", "succeeded", detail="Provider mode: official"
                )
            )

        items = []
        for index, agent in enumerate(selected, start=1):
            start = kwargs.get("on_agent_start")
            if callable(start):
                start(agent, index, len(selected))
            if callable(progress):
                progress(
                    BenchmarkProgress("agent_start", "started", agent.agent_id)
                )
                progress(
                    BenchmarkProgress(
                        "agent_start",
                        "succeeded",
                        agent.agent_id,
                        "FakeAdapter",
                    )
                )
            benchmark = BenchmarkResult(
                agent_id=agent.agent_id,
                adapter_name="FakeAdapter",
                run_id=f"run_{agent.agent_id}",
                run_state="report_ready",
                report=FakeReport(),
                steps=(),
                history_count=1,
                provider_mode="official",
            )
            item = SuiteAgentResult(agent_id=agent.agent_id, benchmark=benchmark)
            items.append(item)
            complete = kwargs.get("on_agent_complete")
            if callable(complete):
                complete(item)
        return BenchmarkSuiteResult(
            selected_agent_ids=tuple(agent.agent_id for agent in selected),
            items=tuple(items),
        )


def test_cli_detects_agent_and_confirms() -> None:
    """Check CLI prints agents and accepts confirm."""
    output: list[str] = []
    delays: list[float] = []
    agents = load_registry(DEFAULT_REGISTRY_PATH).enabled()
    runner = FakeSuiteRunner()

    exit_code = main(
        input_fn=lambda _: "confirm",
        output_fn=output.append,
        suite_runner=runner,  # type: ignore[arg-type]
        sleep_fn=delays.append,
    )

    assert exit_code == 0
    assert len(runner.calls) == 1
    assert output[0] == DEFUZE_LOGO
    for agent in agents:
        assert any(agent.agent_id in line for line in output)
    assert any("Running: [1/3] langgraph-new-project" in line for line in output)
    assert any(f"{ANSI_GREEN}OK{ANSI_RESET}" in line for line in output)
    assert output[-1] == (
        f"\nSuite complete: {len(agents)} passed, 0 failed, 0 skipped, "
        f"{len(agents)} selected."
    )
    _, kwargs = runner.calls[0]
    assert kwargs["allow_local"] is True
    assert kwargs["track_files"] is False
    assert delays == [
        LOGO_PAUSE_SECONDS,
        *([AGENT_REVEAL_DELAY_SECONDS] * (len(agents) + 1)),
    ]


def test_cli_can_cancel() -> None:
    """Check CLI accepts cancel."""
    output: list[str] = []
    runner = FakeSuiteRunner()

    exit_code = main(
        input_fn=lambda _: "cancel",
        output_fn=output.append,
        suite_runner=runner,  # type: ignore[arg-type]
        sleep_fn=lambda _: None,
    )

    assert exit_code == 0
    assert output[-1] == "Cancelled."
    assert runner.calls == []


def test_confirmation_result_can_gate_execution() -> None:
    agents = load_registry(DEFAULT_REGISTRY_PATH).enabled()

    assert confirm_agents(
        agents,
        input_fn=lambda _: "confirm",
        output_fn=lambda _: None,
        sleep_fn=lambda _: None,
    )
    assert not confirm_agents(
        agents,
        input_fn=lambda _: "cancel",
        output_fn=lambda _: None,
        sleep_fn=lambda _: None,
    )


def test_cli_reports_provider_configuration_error() -> None:
    output: list[str] = []
    runner = FakeSuiteRunner(
        error=ProviderSelectionError("DEFUZEX_API_KEY is missing")
    )

    exit_code = main(
        input_fn=lambda _: "confirm",
        output_fn=output.append,
        suite_runner=runner,  # type: ignore[arg-type]
        sleep_fn=lambda _: None,
    )

    assert exit_code == 1
    assert output[-1] == (
        f"{ANSI_RED}【Configuration error】 "
        f"DEFUZEX_API_KEY is missing{ANSI_RESET}"
    )
