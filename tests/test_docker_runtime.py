import json
from types import MappingProxyType

from agentbench.runtime.docker import DockerPolicy
from agentbench.runtime.docker.session import _json_compatible


def test_docker_policy_contains_required_isolation_controls() -> None:
    arguments = DockerPolicy().run_arguments()

    assert "--read-only" in arguments
    assert "--cap-drop=ALL" in arguments
    assert "--security-opt=no-new-privileges" in arguments
    assert any(value.startswith("--memory=") for value in arguments)
    assert any(value.startswith("--cpus=") for value in arguments)
    assert any(value.startswith("--pids-limit=") for value in arguments)


def test_docker_transport_serializes_frozen_sdk_payloads() -> None:
    payload = MappingProxyType(
        {
            "email_input": MappingProxyType({"subject": "Hello"}),
        }
    )

    encoded = json.dumps(payload, default=_json_compatible)

    assert json.loads(encoded) == {"email_input": {"subject": "Hello"}}
