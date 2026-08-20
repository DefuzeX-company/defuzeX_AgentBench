from __future__ import annotations

import sys
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_CONTEXT = REPO_ROOT / "services" / "model-gateway"
GATEWAY_SERVICE_SRC = GATEWAY_CONTEXT / "src"
sys.path.insert(0, str(GATEWAY_SERVICE_SRC))

from defuzex_model_gateway.protocols import (  # noqa: E402
    GatewayAuthenticationError,
    ProtocolRegistry,
    get_protocol,
)

from agentbench.runtime.docker.gateway_image import (  # noqa: E402
    LocalGatewayImageProvider,
    default_gateway_image_provider,
)
from agentbench.runtime.modelgateway import StaticGatewayImageProvider  # noqa: E402


class RecordingImageBuilder:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def build(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return "defuzex-agentbench/model-gateway:test"


def test_gateway_has_an_independent_dependency_manifest() -> None:
    metadata = tomllib.loads(
        (GATEWAY_CONTEXT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert metadata["project"]["name"] == "defuzex-model-gateway"
    assert metadata["project"]["dependencies"] == []


def test_gateway_docker_build_is_scoped_to_its_service_context() -> None:
    builder = RecordingImageBuilder()
    provider = LocalGatewayImageProvider(builder, GATEWAY_CONTEXT)  # type: ignore[arg-type]

    image = provider.resolve_image()

    assert image == "defuzex-agentbench/model-gateway:test"
    assert builder.calls == [
        {
            "context": GATEWAY_CONTEXT,
            "dockerfile": GATEWAY_CONTEXT / "Dockerfile",
            "repository": "model-gateway",
        }
    ]
    dockerfile = (GATEWAY_CONTEXT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY pyproject.toml" in dockerfile
    assert "COPY src" in dockerfile
    assert "COPY agentbench" not in dockerfile


def test_deployment_can_supply_a_published_gateway_image() -> None:
    builder = RecordingImageBuilder()

    provider = default_gateway_image_provider(
        builder,  # type: ignore[arg-type]
        {"DEFUZEX_MODEL_GATEWAY_IMAGE": "registry.example/gateway:1.2.3"},
    )

    assert isinstance(provider, StaticGatewayImageProvider)
    assert provider.resolve_image() == "registry.example/gateway:1.2.3"
    assert builder.calls == []


def test_protocol_registry_accepts_a_trusted_extension() -> None:
    class CustomProtocol:
        name = "custom"

        def authorize(
            self,
            path: str,
            headers: object,
            *,
            gateway_token: str,
            upstream_api_key: str,
        ) -> tuple[str, dict[str, str]]:
            del headers, gateway_token
            return path, {"X-Custom-Key": upstream_api_key}

    registry = ProtocolRegistry()
    registry.register(CustomProtocol())

    protocol = registry.get("CUSTOM")
    assert protocol.authorize(
        "/generate",
        {},
        gateway_token="run-token",
        upstream_api_key="provider-key",
    ) == ("/generate", {"X-Custom-Key": "provider-key"})


def test_openai_protocol_replaces_the_run_token_with_upstream_key() -> None:
    protocol = get_protocol("openai")

    path, headers = protocol.authorize(
        "/v1/chat/completions",
        {
            "Authorization": "Bearer run-token",
            "Content-Type": "application/json",
        },
        gateway_token="run-token",
        upstream_api_key="provider-secret",
    )

    assert path == "/v1/chat/completions"
    assert headers["Authorization"] == "Bearer provider-secret"
    assert headers["Content-Type"] == "application/json"


def test_model_protocol_rejects_an_invalid_run_token() -> None:
    with pytest.raises(GatewayAuthenticationError):
        get_protocol("openai").authorize(
            "/v1/chat/completions",
            {"Authorization": "Bearer wrong"},
            gateway_token="run-token",
            upstream_api_key="provider-secret",
        )
