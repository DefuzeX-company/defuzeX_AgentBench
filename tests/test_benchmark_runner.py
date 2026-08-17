from dataclasses import dataclass
from pathlib import Path

from agentbench.harness import (
    BenchmarkRunner,
    ProviderSelectionError,
    load_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class FakeInput:
    input_id: str
    payload: object


@dataclass(frozen=True)
class FakeReport:
    status: str = "pass"
    confidence: object = 1.0
    issues: tuple[object, ...] = ()
    evidence_gaps: tuple[object, ...] = ()


class FakeSDKRun:
    def __init__(self) -> None:
        self.run_id = "run_test"
        self.state = "ready"
        self.report: FakeReport | None = None
        self.history: tuple[object, ...] = ()
        self._input = FakeInput("input_test", "DEFUZEX_AGENT_READY")
        self._delivered = False

    def get_input(self, *, full: bool = False) -> FakeInput | None:
        assert full
        if self._delivered:
            return None
        self._delivered = True
        self.state = "input_delivered"
        return self._input

    def submit(
        self,
        output: object = None,
        *,
        status: str = "completed",
        error: str | None = None,
    ) -> FakeReport:
        assert output == "DEFUZEX_AGENT_READY"
        assert status == "completed"
        assert error is None
        self.history = (object(),)
        self.report = FakeReport()
        self.state = "report_ready"
        return self.report


class CapturingRunFactory:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    def __call__(self, **kwargs: object) -> FakeSDKRun:
        self.kwargs = kwargs
        return FakeSDKRun()


def registered_agent():  # type: ignore[no-untyped-def]
    registry = load_registry(REPO_ROOT / "resources" / "registry.toml")
    return registry.find("langgraph-new-project")


def test_benchmark_runner_drives_sdk_handshake() -> None:
    registration = registered_agent()
    sdk_run = FakeSDKRun()

    result = BenchmarkRunner().run(registration, sdk_run)

    assert result.passed
    assert result.agent_id == "langgraph-new-project"
    assert result.adapter_name == "LangGraphAdapter"
    assert result.run_state == "report_ready"
    assert result.history_count == 1
    assert len(result.steps) == 1
    assert result.steps[0].input_id == "input_test"
    assert result.steps[0].invocation.output == "DEFUZEX_AGENT_READY"


def test_official_mode_uses_standard_environment_key_and_sdk_judge() -> None:
    factory = CapturingRunFactory()
    runner = BenchmarkRunner(
        sdk_run_factory=factory,
        environ={"DEFUZEX_API_KEY": "dfx_test"},
    )

    result = runner.run_defuzex(
        registered_agent(),
        requirement_path="requirement.md",
        allow_local=True,
        track_files=False,
    )

    assert result.provider_mode == "official"
    assert factory.kwargs is not None
    assert factory.kwargs["api_key"] == "dfx_test"
    assert "case_provider" not in factory.kwargs
    assert "judge_provider" not in factory.kwargs


def test_explicit_provider_pair_selects_local_mode() -> None:
    factory = CapturingRunFactory()
    case_provider = object()
    judge_provider = object()
    runner = BenchmarkRunner(
        sdk_run_factory=factory,
        environ={"DEFUZEX_API_KEY": "dfx_test"},
    )

    result = runner.run_defuzex(
        registered_agent(),
        case_provider=case_provider,
        judge_provider=judge_provider,
        max_inputs=1,
        allow_local=True,
        track_files=False,
    )

    assert result.provider_mode == "local"
    assert factory.kwargs is not None
    assert factory.kwargs["case_provider"] is case_provider
    assert factory.kwargs["judge_provider"] is judge_provider
    assert "api_key" not in factory.kwargs


def test_missing_key_and_providers_stops_before_run_creation() -> None:
    factory = CapturingRunFactory()
    runner = BenchmarkRunner(sdk_run_factory=factory, environ={})

    try:
        runner.run_defuzex(
            registered_agent(),
            requirement_path="requirement.md",
            allow_local=True,
        )
    except ProviderSelectionError as exc:
        assert "DEFUZEX_API_KEY" in str(exc)
    else:
        raise AssertionError("Runner accepted missing official and local Providers")

    assert factory.kwargs is None


def test_partial_local_provider_pair_is_rejected() -> None:
    factory = CapturingRunFactory()
    runner = BenchmarkRunner(sdk_run_factory=factory, environ={})

    try:
        runner.run_defuzex(
            registered_agent(),
            case_provider=object(),
            max_inputs=1,
            allow_local=True,
        )
    except ProviderSelectionError as exc:
        assert "both case_provider and judge_provider" in str(exc)
    else:
        raise AssertionError("Runner accepted a partial local Provider pair")

    assert factory.kwargs is None
