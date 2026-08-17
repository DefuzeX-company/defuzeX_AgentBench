"""Discover registered benchmark agents and request confirmation."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agentbench.harness.registry import AgentRegistration, load_registry


DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2] / "resources" / "registry.toml"
)


def main(
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Show detected agents and ask user to confirm."""

    agents = load_registry(registry_path).enabled()

    if not agents:
        _print_agents(agents, output_fn)
        output_fn("No enabled benchmark agents detected.")
        return 1

    confirm_agents(agents, input_fn=input_fn, output_fn=output_fn)
    return 0


def confirm_agents(
    agents: tuple[AgentRegistration, ...],
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> bool:
    """Print detected agents and return whether execution was confirmed."""

    _print_agents(agents, output_fn)
    try:
        confirmed = _request_confirmation(input_fn, output_fn)
    except (EOFError, KeyboardInterrupt):
        output_fn("\nCancelled.")
        return False

    if not confirmed:
        output_fn("Cancelled.")
        return False

    output_fn(f"Confirmed. {len(agents)} benchmark agent(s) selected.")
    return True


def _print_agents(
    agents: tuple[AgentRegistration, ...], output_fn: Callable[[str], None]
) -> None:
    """Print the detected agent list."""

    output_fn(f"Detected benchmark agents ({len(agents)}):")
    for index, agent in enumerate(agents, start=1):
        output_fn(
            f"  [{index}] {agent.agent_id} | {agent.framework} | {agent.status}\n"
            f"      {agent.path}"
        )


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
