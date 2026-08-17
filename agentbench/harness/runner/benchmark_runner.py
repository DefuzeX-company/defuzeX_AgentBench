"""Execute DefuzeX SDK benchmark runs through registered agents."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from ..errors import AgentInvocationError, ProviderSelectionError
from ..protocols import SDKReport, SDKRun, SDKRunFactory
from ..registry import AgentRegistration
from ..result import BenchmarkResult, BenchmarkStepResult
from .agent_runner import AgentRunner


class BenchmarkRunner:
    """Drive one DefuzeX SDK Run through a registered agent."""

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
        """Select providers, create an SDK Run, and execute it."""

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
        """Execute the SDK get_input/invoke/submit handshake to completion."""

        steps: list[BenchmarkStepResult] = []
        report: SDKReport | None = None
        run_config = {"configurable": {"thread_id": sdk_run.run_id}}

        with self._agent_runner.start(registration) as running:
            adapter_name = running.adapter_name
            while (test_input := sdk_run.get_input(full=True)) is not None:
                try:
                    invocation = running.invoke(
                        test_input.payload,
                        run_config=run_config,
                    )
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
        """Best-effort recording keeps SDK history truthful on agent failure."""

        try:
            sdk_run.submit(
                status="failed",
                error=f"Agent invocation failed: {type(exc).__name__}",
            )
        except Exception:
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
        if has_case_provider and has_judge_provider:
            if requirement_path is not None:
                common["requirement_path"] = requirement_path
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
        resolved_requirement = requirement_path or registration.requirement_path
        if resolved_requirement is None:
            raise ProviderSelectionError(
                "Official DefuzeX Providers require a registered or explicit "
                "requirement_path"
            )
        common["requirement_path"] = resolved_requirement
        common["api_key"] = resolved_key
        return "official", common

    def _official_api_key(self, explicit: str | None) -> str | None:
        """Resolve the API key without logging secrets."""

        return explicit or self._environ.get("DEFUZEX_API_KEY")


def _create_defuzex_run(**kwargs: object) -> SDKRun:
    """Import the SDK lazily so agent-only usage remains lightweight."""

    try:
        from defuzex import create_run
    except ModuleNotFoundError as exc:
        raise ProviderSelectionError(
            "DefuzeX SDK is not installed in the active Python environment"
        ) from exc
    return create_run(**kwargs)  # type: ignore[arg-type, return-value]
