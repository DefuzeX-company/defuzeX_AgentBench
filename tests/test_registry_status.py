from pathlib import Path

import pytest

from agentbench.cli.registry_status import RegistryStatusError, update_agent_status


def test_update_agent_status_changes_only_the_target_block(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.toml"
    registry_path.write_text(
        'schema_version = "defuzex-bench.registry.v1"\n\n'
        "[[agents]]\n"
        'agent_id = "first"\n'
        'status = "adapting" # promote me\n\n'
        "[[agents]]\n"
        'agent_id = "second"\n'
        'status = "adapting"\n',
        encoding="utf-8",
    )

    update_agent_status(
        registry_path,
        "first",
        expected_status="adapting",
        new_status="ready",
    )

    assert registry_path.read_text(encoding="utf-8") == (
        'schema_version = "defuzex-bench.registry.v1"\n\n'
        "[[agents]]\n"
        'agent_id = "first"\n'
        'status = "ready" # promote me\n\n'
        "[[agents]]\n"
        'agent_id = "second"\n'
        'status = "adapting"\n'
    )


def test_update_agent_status_detects_concurrent_status_change(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.toml"
    registry_path.write_text(
        "[[agents]]\n"
        'agent_id = "test-agent"\n'
        'status = "blocked"\n',
        encoding="utf-8",
    )

    with pytest.raises(RegistryStatusError, match="changed"):
        update_agent_status(
            registry_path,
            "test-agent",
            expected_status="adapting",
            new_status="ready",
        )
