import json
from pathlib import Path

from agentbench.cli.main import cli
from agentbench.cli.features.certify import certify
from agentbench.harness.registry import load_registry
from tests.test_cli import FakeSuiteRunner


def test_cli_dispatches_certify_command(monkeypatch) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_certify(agent_id, *, output_path):  # type: ignore[no-untyped-def]
        calls.append((agent_id, output_path))
        return 6

    monkeypatch.setattr("agentbench.cli.features.certify.certify", fake_certify)

    assert cli(["certify", "test-agent"]) == 6
    assert calls == [("test-agent", None)]


def test_certify_promotes_passing_adapting_agent(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path, status="adapting")
    output: list[str] = []

    exit_code = certify(
        "test-agent",
        registry_path=registry_path,
        output_fn=output.append,
        suite_runner=FakeSuiteRunner(),  # type: ignore[arg-type]
    )

    assert exit_code == 0
    assert load_registry(registry_path).find("test-agent").status == "ready"
    artifacts = list(tmp_path.glob("results/certify-test-agent-*.jsonl"))
    assert len(artifacts) == 1
    events = [
        json.loads(line)
        for line in artifacts[0].read_text(encoding="utf-8").splitlines()
    ]
    assert events[-1]["summary"]["suite_passed"] is True
    assert output[-1] == "Certification passed. Agent 'test-agent' is now ready."


def test_certify_keeps_failing_agent_adapting(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path, status="adapting")
    output: list[str] = []

    exit_code = certify(
        "test-agent",
        registry_path=registry_path,
        output_fn=output.append,
        suite_runner=FakeSuiteRunner(result_status="issue"),  # type: ignore[arg-type]
    )

    assert exit_code == 1
    assert load_registry(registry_path).find("test-agent").status == "adapting"
    assert output[-1] == "Certification failed. Agent 'test-agent' remains adapting."


def test_certify_is_idempotent_for_ready_agent(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path, status="ready")
    runner = FakeSuiteRunner()
    output: list[str] = []

    exit_code = certify(
        "test-agent",
        registry_path=registry_path,
        output_fn=output.append,
        suite_runner=runner,  # type: ignore[arg-type]
    )

    assert exit_code == 0
    assert runner.calls == []
    assert output == ["Agent 'test-agent' is already ready."]


def test_certify_rejects_non_adapting_status(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path, status="planned")

    exit_code = certify(
        "test-agent",
        registry_path=registry_path,
        output_fn=lambda _: None,
        suite_runner=FakeSuiteRunner(),  # type: ignore[arg-type]
    )

    assert exit_code == 2
    assert load_registry(registry_path).find("test-agent").status == "planned"


def _write_registry(tmp_path: Path, *, status: str) -> Path:
    resources = tmp_path / "resources"
    agent_path = resources / "agents" / "test-agent"
    requirement_path = resources / "requirements" / "test-agent.md"
    agent_path.mkdir(parents=True)
    requirement_path.parent.mkdir(parents=True)
    (agent_path / "agent.toml").write_text(
        'agent_id = "test-agent"\n', encoding="utf-8"
    )
    requirement_path.write_text("# Test requirement\n", encoding="utf-8")
    registry_path = resources / "registry.toml"
    registry_path.write_text(
        'schema_version = "defuzex-bench.registry.v1"\n\n'
        "[[agents]]\n"
        '# Keep this comment and field order.\n'
        'agent_id = "test-agent"\n'
        'path = "resources/agents/test-agent"\n'
        'enabled = true\n'
        f'status = "{status}" # lifecycle\n'
        'framework = "langgraph"\n'
        'source = "https://example.com/test-agent"\n',
        encoding="utf-8",
    )
    return registry_path
