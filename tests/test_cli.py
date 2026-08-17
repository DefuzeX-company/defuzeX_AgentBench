from agentbench.cli.main import DEFAULT_REGISTRY_PATH, confirm_agents, main
from agentbench.harness import load_registry


def test_cli_detects_agent_and_confirms() -> None:
    """Check CLI prints agents and accepts confirm."""
    output: list[str] = []
    agents = load_registry(DEFAULT_REGISTRY_PATH).enabled()

    exit_code = main(input_fn=lambda _: "confirm", output_fn=output.append)

    assert exit_code == 0
    for agent in agents:
        assert any(agent.agent_id in line for line in output)
    assert output[-1] == f"Confirmed. {len(agents)} benchmark agent(s) selected."


def test_cli_can_cancel() -> None:
    """Check CLI accepts cancel."""
    output: list[str] = []

    exit_code = main(input_fn=lambda _: "cancel", output_fn=output.append)

    assert exit_code == 0
    assert output[-1] == "Cancelled."


def test_confirmation_result_can_gate_execution() -> None:
    agents = load_registry(DEFAULT_REGISTRY_PATH).enabled()

    assert confirm_agents(
        agents, input_fn=lambda _: "confirm", output_fn=lambda _: None
    )
    assert not confirm_agents(
        agents, input_fn=lambda _: "cancel", output_fn=lambda _: None
    )
