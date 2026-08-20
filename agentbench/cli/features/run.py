"""Run all enabled, ready benchmark agents."""

from __future__ import annotations

import time
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from pathlib import Path

from agentbench.harness import SuiteRunner
from agentbench.harness.registry import load_registry

from agentbench.cli.constants import ANSI_GREEN, LOGO_PAUSE_SECONDS
from agentbench.cli.execution import run_benchmark_once, stop_viewer
from agentbench.cli.logo import print_logo
from agentbench.cli.presentation import (
    confirm_agents,
    panel_line,
    panel_rule,
    print_agents,
    request_viewer_action,
)
from agentbench.cli.viewer import RunningViewer, start_viewer_server

from .base import CommandFeature

DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parents[3] / "resources" / "registry.toml"
)


def configure_parser(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        metavar="PATH",
        help=(
            "Write a unique append-only JSONL result artifact, including "
            "trace-like step data."
        ),
    )


def execute(args: Namespace) -> int:
    return run(output_path=args.output)


def run(
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
    """Confirm ready Agents, run the suite, and return a shell exit code."""

    print_logo(output_fn)
    sleep_fn(LOGO_PAUSE_SECONDS)

    registry = load_registry(registry_path)
    agents = registry.ready()
    if not agents:
        print_agents(agents, output_fn)
        output_fn("No enabled ready benchmark agents detected.")
        return 1

    adapting = registry.enabled_with_status("adapting")
    if adapting:
        agent_word = "Agent" if len(adapting) == 1 else "Agents"
        output_fn(
            f"{len(adapting)} adapting {agent_word} excluded from this run. "
            "Use 'agentbench certify <agent_id>' when an adapter is ready."
        )

    if not confirm_agents(
        agents,
        input_fn=input_fn,
        output_fn=output_fn,
        sleep_fn=sleep_fn,
    ):
        return 0

    runner = suite_runner or SuiteRunner()
    while True:
        execution = run_benchmark_once(
            agents,
            runner=runner,
            output_path=output_path,
            output_fn=output_fn,
            viewer_starter=viewer_starter,
        )
        if execution.result_log is None or execution.viewer is None:
            return execution.exit_code

        action = request_viewer_action(
            execution.result_log.path,
            execution.viewer.url,
            input_fn=post_run_input_fn,
            output_fn=output_fn,
        )
        stop_viewer(execution.viewer)
        if action == "rerun":
            output_fn("")
            output_fn(panel_rule("RERUN QUEUED", ANSI_GREEN))
            output_fn(panel_line("Starting a fresh benchmark run"))
            output_fn(panel_rule("", ANSI_GREEN))
            continue
        return execution.exit_code


FEATURE = CommandFeature(
    name="run",
    help="Run all enabled Agents whose status is ready.",
    description="Discover, confirm, and benchmark registered ready Agents.",
    configure=configure_parser,
    execute=execute,
    default=True,
)
