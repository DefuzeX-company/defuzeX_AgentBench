"""Certify one adapting Agent and promote it to ready."""

from __future__ import annotations

import re
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from pathlib import Path

from agentbench.harness import SuiteRunner
from agentbench.harness.registry import load_registry

from agentbench.cli.execution import run_benchmark_once
from agentbench.cli.registry_status import RegistryStatusError, update_agent_status

from .base import CommandFeature
from .run import DEFAULT_REGISTRY_PATH


def configure_parser(parser: ArgumentParser) -> None:
    parser.add_argument("agent_id", help="Registered adapting Agent to certify.")
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Optional base path for the append-only certification result.",
    )


def execute(args: Namespace) -> int:
    return certify(args.agent_id, output_path=args.output)


def certify(
    agent_id: str,
    *,
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
    output_path: str | Path | None = None,
    output_fn: Callable[[str], None] = print,
    suite_runner: SuiteRunner | None = None,
) -> int:
    """Run one adapting Agent and promote it only after a passing suite."""

    registry = load_registry(registry_path)
    try:
        agent = registry.find(agent_id)
    except (KeyError, ValueError) as exc:
        output_fn(f"Certification error: {exc}")
        return 2

    if agent.status == "ready":
        output_fn(f"Agent '{agent_id}' is already ready.")
        return 0
    if agent.status != "adapting":
        output_fn(
            f"Certification error: Agent '{agent_id}' has status "
            f"'{agent.status}', expected 'adapting'."
        )
        return 2

    artifact_base = output_path or _default_output_path(registry_path, agent_id)
    output_fn(f"Certifying adapting Agent: {agent_id}")
    output_fn("The registry will change to ready only if the full suite passes.")
    execution = run_benchmark_once(
        (agent,),
        runner=suite_runner or SuiteRunner(),
        output_path=artifact_base,
        output_fn=output_fn,
        viewer_starter=None,
    )
    if execution.exit_code != 0:
        output_fn(f"Certification failed. Agent '{agent_id}' remains adapting.")
        return execution.exit_code

    try:
        update_agent_status(
            registry_path,
            agent_id,
            expected_status="adapting",
            new_status="ready",
        )
    except RegistryStatusError as exc:
        output_fn(f"Certification passed, but registry update failed: {exc}")
        return 2

    output_fn(f"Certification passed. Agent '{agent_id}' is now ready.")
    return 0


def _default_output_path(registry_path: str | Path, agent_id: str) -> Path:
    repo_root = Path(registry_path).resolve().parent.parent
    safe_agent_id = re.sub(r"[^A-Za-z0-9._-]+", "-", agent_id).strip("-")
    return repo_root / "results" / f"certify-{safe_agent_id or 'agent'}.jsonl"


FEATURE = CommandFeature(
    name="certify",
    help="Run one adapting Agent and promote it to ready on success.",
    description=(
        "Execute the full benchmark flow for one adapting Agent and update "
        "its registry status only after a passing suite."
    ),
    configure=configure_parser,
    execute=execute,
)
