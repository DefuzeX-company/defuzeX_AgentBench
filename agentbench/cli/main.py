"""Discover, confirm, and benchmark registered Agents."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
import re

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
) -> int:
    """Confirm discovered Agents, run the suite, and return a shell exit code."""

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
    progress_printer = ProgressPrinter(output_fn)
    try:
        result = runner.run_defuzex(
            agents,
            allow_local=True,
            track_files=False,
            on_agent_start=lambda agent, index, total: _print_agent_start(
                agent, index, total, output_fn
            ),
            on_agent_complete=lambda item: _print_agent_complete(item, output_fn),
            on_progress=progress_printer,
        )
    except (ProviderSelectionError, SuiteConfigurationError) as exc:
        output_fn(configuration_error(exc))
        return 1

    _print_suite_summary(result, output_fn)
    return 0 if result.passed else 1


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
            f"{ANSI_GREEN}OK{ANSI_RESET}  "
            f"{len(agents)} benchmark agent(s) selected"
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
                f"    status: {status}"
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
    """Ask user to confirm or cancel the run."""

    while True:
        answer = input_fn("Continue? [confirm/cancel]: ").strip().lower()
        if answer in {"confirm", "c", "yes", "y"}:
            return True
        if answer in {"cancel", "n", "no", ""}:
            return False
        output_fn("Enter 'confirm' or 'cancel'.")


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
    if item.error_type is not None:
        output_fn(
            f"Result: {ANSI_RED}FAILED{ANSI_RESET} | "
            f"{item.error_type}: {item.error_message}"
        )
        return

    benchmark = item.benchmark
    if benchmark is None:  # pragma: no cover - enforced by SuiteAgentResult
        raise RuntimeError("Suite result has neither a benchmark nor an error")
    status = (
        f"{ANSI_GREEN}PASS{ANSI_RESET}"
        if benchmark.passed
        else f"{ANSI_RED}FAIL{ANSI_RESET}"
    )
    output_fn(
        f"Result: {status} | run={benchmark.run_id} | "
        f"inputs={benchmark.history_count}"
    )


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
