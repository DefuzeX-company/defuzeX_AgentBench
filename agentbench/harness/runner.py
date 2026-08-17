"""Start and manage registered benchmark agents without SDK concerns."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from agentbench.adapter import (
    DEFAULT_ADAPTER_FACTORY,
    AdapterFactory,
    AdapterInvocation,
    AgentAdapter,
)

from .registry import AgentRegistration
from .result import BenchmarkResult, BenchmarkStepResult, SDKReport


class AgentStartError(RuntimeError):
    """Raised when a registered agent cannot be loaded."""


class AgentNotRunningError(RuntimeError):
    """Raised when a stopped agent is invoked."""


class AgentInvocationError(RuntimeError):
    """Raised when an Agent fails while processing an SDK Input."""


class ProviderSelectionError(RuntimeError):
    """Raised before Agent startup when no valid SDK Provider mode is available."""


class SDKTestInput(Protocol):
    """Subset of DefuzeXInput required by the Harness."""

    input_id: str
    payload: object


class SDKRun(Protocol):
    """Strict-handshake subset of defuzex.Run required by the Harness."""

    run_id: str
    state: str
    report: SDKReport | None
    history: tuple[object, ...]

    def get_input(self, *, full: bool = False) -> SDKTestInput | None:
        ...

    def submit(
        self,
        output: object = None,
        *,
        status: str = "completed",
        error: str | None = None,
    ) -> SDKReport | None:
        ...


class SDKRunFactory(Protocol):
    """Callable shape of defuzex.create_run used for dependency injection."""

    def __call__(self, **kwargs: object) -> SDKRun:
        ...


@dataclass(slots=True)
class RunningAgent:
    """A loaded agent and its framework-neutral invocation handle."""

    registration: AgentRegistration
    adapter: AgentAdapter
    _stopped: bool = field(default=False, init=False, repr=False)

    @property
    def agent_id(self) -> str:
        return self.registration.agent_id

    @property
    def adapter_name(self) -> str:
        return type(self.adapter).__name__

    @property
    def is_running(self) -> bool:
        return not self._stopped and self.adapter.is_loaded

    def invoke(
        self, value: object, *, run_config: object | None = None
    ) -> AdapterInvocation:
        if not self.is_running:
            raise AgentNotRunningError(f"Agent is not running: {self.agent_id}")
        return self.adapter.invoke(value, run_config=run_config)

    async def ainvoke(
        self, value: object, *, run_config: object | None = None
    ) -> AdapterInvocation:
        if not self.is_running:
            raise AgentNotRunningError(f"Agent is not running: {self.agent_id}")
        return await self.adapter.ainvoke(value, run_config=run_config)

    def stop(self) -> None:
        if self._stopped:
            return
        self.adapter.close()
        self._stopped = True

    def __enter__(self) -> "RunningAgent":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()


class AgentRunner:
    """Create an adapter and load one registered agent."""

    def __init__(
        self, *, adapter_factory: AdapterFactory = DEFAULT_ADAPTER_FACTORY
    ) -> None:
        self._adapter_factory = adapter_factory

    def start(self, agent: AgentRegistration) -> RunningAgent:
        adapter = self._adapter_factory.create(agent)
        try:
            adapter.load()
        except Exception as exc:
            adapter.close()
            raise AgentStartError(f"Failed to start agent {agent.agent_id!r}") from exc
        return RunningAgent(registration=agent, adapter=adapter)


class BenchmarkRunner:
    """Drive one DefuzeX SDK Run through a registered Agent."""

    def __init__(
        self,
        *,
        agent_runner: AgentRunner | None = None,
        sdk_run_factory: SDKRunFactory | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._agent_runner = agent_runner or AgentRunner()
        self._sdk_run_factory = sdk_run_factory or _create_defuzex_run
        self._environ = os.environ if environ is None else environ

    def run_defuzex(
        self,
        registration: AgentRegistration,
        *,
        requirement_path: str | Path | None = None,
        case_provider: object | None = None,
        judge_provider: object | None = None,
        api_key: str | None = None,
        max_inputs: int | None = None,
        allow_local: bool = False,
        track_files: bool = True,
        save_local: bool = False,
    ) -> BenchmarkResult:
        """Select custom or official SDK Providers, create a Run, and execute it.

        Passing both Providers explicitly selects fully local mode. With no
        Providers, an API key is required and the SDK selects its official Case
        and Judge Providers. A partial Provider pair is rejected to avoid an
        accidental local/official hybrid run.
        """

        provider_mode, run_kwargs = self._sdk_run_configuration(
            registration=registration,
            requirement_path=requirement_path,
            case_provider=case_provider,
            judge_provider=judge_provider,
            api_key=api_key,
            max_inputs=max_inputs,
            allow_local=allow_local,
            track_files=track_files,
            save_local=save_local,
        )
        sdk_run = self._sdk_run_factory(**run_kwargs)
        result = self.run(registration, sdk_run)
        return BenchmarkResult(
            agent_id=result.agent_id,
            adapter_name=result.adapter_name,
            run_id=result.run_id,
            run_state=result.run_state,
            report=result.report,
            steps=result.steps,
            history_count=result.history_count,
            provider_mode=provider_mode,
        )

    def run(
        self, registration: AgentRegistration, sdk_run: SDKRun
    ) -> BenchmarkResult:
        """Execute the SDK's get_input/invoke/submit handshake to completion."""

        steps: list[BenchmarkStepResult] = []
        report: SDKReport | None = None

        with self._agent_runner.start(registration) as running:
            adapter_name = running.adapter_name
            while (test_input := sdk_run.get_input(full=True)) is not None:
                # The SDK's public payload is the Agent input. Input IDs remain
                # Harness metadata and are retained in BenchmarkStepResult.
                try:
                    invocation = running.invoke(test_input.payload)
                except Exception as exc:
                    self._record_failed_submission(sdk_run, exc)
                    raise AgentInvocationError(
                        f"Agent {registration.agent_id!r} failed for "
                        f"SDK Input {test_input.input_id!r}"
                    ) from exc

                steps.append(
                    BenchmarkStepResult(
                        input_id=test_input.input_id,
                        payload=test_input.payload,
                        invocation=invocation,
                    )
                )
                report = sdk_run.submit(invocation.output)

        if report is None:
            report = sdk_run.report
        return BenchmarkResult(
            agent_id=registration.agent_id,
            adapter_name=adapter_name,
            run_id=sdk_run.run_id,
            run_state=sdk_run.state,
            report=report,
            steps=tuple(steps),
            history_count=len(sdk_run.history),
        )

    @staticmethod
    def _record_failed_submission(sdk_run: SDKRun, exc: Exception) -> None:
        """Best-effort recording keeps SDK history truthful on Agent failure."""

        try:
            sdk_run.submit(
                status="failed",
                error=f"Agent invocation failed: {type(exc).__name__}",
            )
        except Exception:
            # Preserve the original Agent exception if SDK failure recording also fails.
            pass

    def _sdk_run_configuration(
        self,
        *,
        registration: AgentRegistration,
        requirement_path: str | Path | None,
        case_provider: object | None,
        judge_provider: object | None,
        api_key: str | None,
        max_inputs: int | None,
        allow_local: bool,
        track_files: bool,
        save_local: bool,
    ) -> tuple[str, dict[str, object]]:
        has_case_provider = case_provider is not None
        has_judge_provider = judge_provider is not None
        if has_case_provider != has_judge_provider:
            raise ProviderSelectionError(
                "Provide both case_provider and judge_provider for local mode"
            )

        common: dict[str, object] = {
            "repo_path": registration.path,
            "allow_local": allow_local,
            "track_files": track_files,
            "save_local": save_local,
        }
        if requirement_path is not None:
            common["requirement_path"] = requirement_path

        if has_case_provider and has_judge_provider:
            if max_inputs is None:
                raise ProviderSelectionError(
                    "Local custom Providers require max_inputs"
                )
            common.update(
                case_provider=case_provider,
                judge_provider=judge_provider,
                max_inputs=max_inputs,
            )
            return "local", common

        resolved_key = self._official_api_key(api_key)
        if resolved_key is None:
            raise ProviderSelectionError(
                "No DefuzeX API key or local Provider pair is configured. Set "
                "DEFUZEX_API_KEY or provide both case_provider and "
                "judge_provider."
            )
        if requirement_path is None:
            raise ProviderSelectionError(
                "Official DefuzeX Providers require requirement_path"
            )
        common["api_key"] = resolved_key
        return "official", common

    def _official_api_key(self, explicit: str | None) -> str | None:
        """Resolve without logging secrets; the SDK performs format validation."""

        return (
            explicit
            or self._environ.get("DEFUZEX_API_KEY")
        )


def _create_defuzex_run(**kwargs: object) -> SDKRun:
    """Import the SDK lazily so Agent-only Runner usage remains lightweight."""

    try:
        from defuzex import create_run
    except ModuleNotFoundError as exc:
        raise ProviderSelectionError(
            "DefuzeX SDK is not installed in the active Python environment"
        ) from exc
    return create_run(**kwargs)  # type: ignore[arg-type, return-value]
