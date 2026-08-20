"""Discover, confirm, and benchmark registered Agents."""

from __future__ import annotations

import re
import sys
import time
from argparse import ArgumentParser
from collections.abc import Callable
from pathlib import Path
from typing import Sequence
from urllib.parse import quote

from agentbench.harness import (
    ProviderSelectionError,
    SuiteAgentResult,
    SuiteConfigurationError,
    SuiteRunner,
)
from agentbench.harness.registry import AgentRegistration, load_registry
from agentbench.harness.result import BenchmarkSuiteResult

from .constants import (
    AGENT_REVEAL_DELAY_SECONDS,
    AGENT_SEPARATOR_WIDTH,
    ANSI_BLUE,
    ANSI_BOLD,
    ANSI_CYAN,
    ANSI_GREEN,
    ANSI_MAGENTA,
    ANSI_RED,
    ANSI_RESET,
    LOGO_PAUSE_SECONDS,
)
from .logo import print_logo
from .progress import (
    ProgressPrinter,
    configuration_error,
)
from .result_export import ResultLogWriter, start_result_log
from .viewer import RunningViewer, start_viewer_server, view_cli

DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2] / "resources" / "registry.toml"
)
PANEL_WIDTH = AGENT_SEPARATOR_WIDTH
PANEL_INNER_WIDTH = PANEL_WIDTH - 2
ANSI_PATTERN = re.compile(r"\033\[[0-9;]*m")


def main(
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    suite_runner: SuiteRunner | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    output_path: str | Path | None = None,
    viewer_starter: Callable[[Path], RunningViewer] = start_viewer_server,
    post_run_input_fn: Callable[[str], str] = input,
) -> int:
    """Confirm discovered Agents, run the suite, and return a shell exit code."""

    if _should_dispatch_legacy_cli(
        output_path=output_path,
        input_fn=input_fn,
        output_fn=output_fn,
        suite_runner=suite_runner,
        sleep_fn=sleep_fn,
    ):
        return cli(sys.argv[1:])

    print_logo(output_fn)
    sleep_fn(LOGO_PAUSE_SECONDS)

    agents = load_registry(registry_path).enabled()
    if not agents:
        _print_agents(agents, output_fn)
        output_fn("No enabled benchmark agents detected.")
        return 1

    if not confirm_agents(
        agents,
        input_fn=input_fn,
        output_fn=output_fn,
        sleep_fn=sleep_fn,
    ):
        return 0

    runner = suite_runner or SuiteRunner()
    while True:
        exit_code, result_log, viewer = _run_benchmark_once(
            agents,
            runner=runner,
            output_path=output_path,
            output_fn=output_fn,
            viewer_starter=viewer_starter,
        )
        if result_log is None or viewer is None:
            return exit_code

        action = _request_viewer_action(
            result_log.path,
            viewer.url,
            input_fn=post_run_input_fn,
            output_fn=output_fn,
        )
        _stop_viewer(viewer)
        if action == "rerun":
            output_fn("")
            output_fn(_panel_rule("RERUN QUEUED", ANSI_GREEN))
            output_fn(_panel_line("Starting a fresh benchmark run"))
            output_fn(_panel_rule("", ANSI_GREEN))
            continue
        return exit_code


def cli(argv: Sequence[str] | None = None) -> int:
    """Parse command-line arguments and run AgentBench."""

    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list and args_list[0] == "view":
        return view_cli(args_list[1:])

    parser = ArgumentParser(
        prog="agentbench",
        description="Discover, confirm, and benchmark registered Agents.",
    )

    parser.add_argument(
        "--output",
        metavar="PATH",
        help=(
            "Write a unique append-only JSONL result artifact, including "
            "trace-like step data."
        ),
    )
    args = parser.parse_args(args_list)
    return main(output_path=args.output)


def _run_benchmark_once(
    agents: tuple[AgentRegistration, ...],
    *,
    runner: SuiteRunner,
    output_path: str | Path | None,
    output_fn: Callable[[str], None],
    viewer_starter: Callable[[Path], RunningViewer],
) -> tuple[int, ResultLogWriter | None, RunningViewer | None]:
    suite_id = runner.new_suite_id()
    result_log: ResultLogWriter | None = None
    viewer: RunningViewer | None = None
    # With --output we create a unique append-only JSONL artifact containing
    # trace-like step payloads and raw adapter states; without it, no trace
    # artifact is written.
    if output_path is not None:
        result_log = start_result_log(
            output_path,
            suite_id=suite_id,
            selected_agent_ids=tuple(agent.agent_id for agent in agents),
        )
        viewer = viewer_starter(result_log.path)
        output_fn(f"Suite ID: {suite_id}")
        output_fn(f"Result artifact started: {result_log.path}")
        output_fn(f"View: {viewer.url}")

    progress_printer = ProgressPrinter(output_fn)
    try:
        result = runner.run_defuzex(
            agents,
            suite_id=suite_id,
            allow_local=True,
            track_files=False,
            on_agent_start=lambda agent, index, total: _print_agent_start(
                agent, index, total, output_fn
            ),
            on_agent_complete=lambda item: _handle_agent_complete(
                item,
                output_fn,
                result_log,
                None if viewer is None else viewer.url,
            ),
            on_progress=progress_printer,
            on_step_start=(
                None if result_log is None else result_log.append_step_started
            ),
            on_step_complete=(
                None if result_log is None else result_log.append_step_completed
            ),
            on_step_failure=(
                None if result_log is None else result_log.append_step_failed
            ),
        )
    except (ProviderSelectionError, SuiteConfigurationError) as exc:
        if result_log is not None:
            result_log.append_suite_error(exc)
        output_fn(configuration_error(exc))
        if result_log is not None:
            _print_viewer_footer(
                result_log.path, None if viewer is None else viewer.url, output_fn
            )
        return 1, result_log, viewer

    if result_log is not None:
        result_log.append_suite_complete(result)

    _print_suite_summary(result, output_fn)
    if result_log is not None:
        _print_viewer_footer(
            result_log.path, None if viewer is None else viewer.url, output_fn
        )
    return 0 if result.passed else 1, result_log, viewer


def _print_viewer_footer(
    result_log_path: Path,
    viewer_url: str | None,
    output_fn: Callable[[str], None],
) -> None:
    output_fn("")
    output_fn(_panel_rule("RESULT VIEWER", ANSI_CYAN))
    output_fn(_panel_line(f"Result saved: {result_log_path}"))
    if viewer_url is not None:
        output_fn(_panel_line(f"Live viewer: {viewer_url}"))
    output_fn(_panel_line(f"Open later: python -m agentbench view {result_log_path}"))
    output_fn(_panel_rule("", ANSI_CYAN))


def _request_viewer_action(
    result_log_path: Path,
    viewer_url: str,
    *,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> str:
    output_fn(f"Viewer is running at {viewer_url}. Result log: {result_log_path}")
    while True:
        try:
            answer = input_fn("Viewer action? [r rerun/q quit]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            output_fn("\nViewer stopped.")
            return "quit"
        if answer in {"q", "quit", "exit", ""}:
            output_fn("Viewer stopped.")
            return "quit"
        if answer in {"r", "rerun", "retry", "again"}:
            output_fn("Viewer stopped. Rerunning benchmark.")
            return "rerun"
        output_fn("Enter 'r' to rerun or 'q' to quit.")


def _stop_viewer(viewer: RunningViewer) -> None:
    stop = getattr(viewer, "stop", None)
    if callable(stop):
        stop()


def _should_dispatch_legacy_cli(
    *,
    output_path: str | Path | None,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
    suite_runner: SuiteRunner | None,
    sleep_fn: Callable[[float], None],
) -> bool:
    """Support stale console scripts that still call main() directly."""

    args = sys.argv[1:]
    return (
        output_path is None
        and input_fn is input
        and output_fn is print
        and suite_runner is None
        and sleep_fn is time.sleep
        and bool(args)
        and (args[0] == "view" or args[0].startswith("-"))
    )


def confirm_agents(
    agents: tuple[AgentRegistration, ...],
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    sleep_fn: Callable[[float], None] = time.sleep,
    reveal_delay: float = AGENT_REVEAL_DELAY_SECONDS,
) -> bool:
    """Print detected agents and return whether execution was confirmed."""

    _print_agents(
        agents,
        output_fn,
        sleep_fn=sleep_fn,
        reveal_delay=reveal_delay,
    )
    try:
        confirmed = _request_confirmation(input_fn, output_fn)
    except (EOFError, KeyboardInterrupt):
        output_fn("\nCancelled.")
        return False

    if not confirmed:
        output_fn("Cancelled.")
        return False

    output_fn("")
    output_fn(_panel_rule("RUN QUEUED", ANSI_GREEN))
    output_fn(
        _panel_line(
            f"{ANSI_GREEN}OK{ANSI_RESET}  {len(agents)} benchmark agent(s) selected"
        )
    )
    output_fn(_panel_line("Next stage: DefuzeX SDK configuration check"))
    output_fn(_panel_rule("", ANSI_GREEN))
    return True


def _print_agents(
    agents: tuple[AgentRegistration, ...],
    output_fn: Callable[[str], None],
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
    reveal_delay: float = AGENT_REVEAL_DELAY_SECONDS,
) -> None:
    """Print the detected agent list."""

    output_fn("")
    output_fn(_panel_rule("AGENT DISCOVERY", ANSI_CYAN))
    output_fn(
        _panel_line(
            f"{ANSI_BOLD}Detected benchmark agents:{ANSI_RESET} "
            f"{len(agents)} ready for selection"
        )
    )
    output_fn(_panel_line(""))
    for index, agent in enumerate(agents, start=1):
        sleep_fn(reveal_delay)
        marker = f"{ANSI_MAGENTA}{index:02d}{ANSI_RESET}"
        status = (
            f"{ANSI_GREEN}{agent.status.upper()}{ANSI_RESET}"
            if agent.status == "ready"
            else agent.status.upper()
        )
        output_fn(_panel_line(f"{marker}  {agent.agent_id}"))
        output_fn(
            _panel_line(
                f"    framework: {ANSI_BLUE}{agent.framework}{ANSI_RESET}"
                f"    status: {status}    cases: {agent.case_count}"
            )
        )
        output_fn(_panel_line(f"    path: {_display_path(agent.path)}"))
        if index < len(agents):
            output_fn(_panel_line("    " + "." * 64))
    if agents:
        sleep_fn(reveal_delay)
    output_fn(_panel_rule("", ANSI_CYAN))


def _request_confirmation(
    input_fn: Callable[[str], str], output_fn: Callable[[str], None]
) -> bool:
    """Ask user to approve or decline the run."""

    while True:
        answer = input_fn("Continue? [yes/no]: ").strip().lower()
        if answer in {"confirm", "c", "yes", "y"}:
            return True
        if answer in {"cancel", "n", "no", ""}:
            return False
        output_fn("Enter 'yes' or 'no'.")


def _print_agent_start(
    agent: AgentRegistration,
    index: int,
    total: int,
    output_fn: Callable[[str], None],
) -> None:
    output_fn("\n" + "-" * AGENT_SEPARATOR_WIDTH)
    output_fn(f"Running: [{index}/{total}] {agent.agent_id}")


def _print_agent_complete(
    item: SuiteAgentResult, output_fn: Callable[[str], None]
) -> None:
    if item.error_type is not None and item.completed_case_count == 0:
        output_fn(
            f"Result: {ANSI_RED}FAILED{ANSI_RESET} | "
            f"{item.error_type}: {item.error_message}"
        )
        return

    status = (
        f"{ANSI_GREEN}PASS{ANSI_RESET}"
        if item.passed
        else f"{ANSI_RED}FAIL{ANSI_RESET}"
    )
    detail = (
        f"Result: {status} | "
        f"cases={item.completed_case_count}/{item.requested_case_count}"
    )
    if item.error_type is not None:
        detail += f" | stopped={item.error_type}: {item.error_message}"
    output_fn(detail)


def _handle_agent_complete(
    item: SuiteAgentResult,
    output_fn: Callable[[str], None],
    result_log: ResultLogWriter | None,
    viewer_url: str | None,
) -> None:
    _print_agent_complete(item, output_fn)
    if result_log is not None:
        result_log.append_agent_complete(item)
    if viewer_url is not None:
        output_fn(f"View: {_agent_view_url(viewer_url, item.agent_id)}")


def _agent_view_url(viewer_url: str, agent_id: str) -> str:
    separator = "" if viewer_url.endswith("/") else "/"
    return f"{viewer_url}{separator}#agent={quote(agent_id, safe='')}"


def _print_suite_summary(
    result: BenchmarkSuiteResult, output_fn: Callable[[str], None]
) -> None:
    output_fn(
        "\nSuite complete: "
        f"{result.passed_count} passed, "
        f"{result.failed_count} failed, "
        f"{result.skipped_count} skipped, "
        f"{result.selected_count} selected."
    )


def _panel_rule(title: str, color: str) -> str:
    if not title:
        return f"{color}+{'-' * PANEL_INNER_WIDTH}+{ANSI_RESET}"

    label = f" {title} "
    right = PANEL_INNER_WIDTH - len(label)
    return f"{color}+{label}{'-' * right}+{ANSI_RESET}"


def _panel_line(text: str) -> str:
    content = f" {text}"
    padding = max(PANEL_INNER_WIDTH - _visible_width(content), 0)
    return f"{ANSI_CYAN}|{ANSI_RESET}{content}{' ' * padding}{ANSI_CYAN}|{ANSI_RESET}"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(DEFAULT_REGISTRY_PATH.parents[1]))
    except ValueError:
        return str(path)


def _visible_width(text: str) -> int:
    return len(ANSI_PATTERN.sub("", text))
