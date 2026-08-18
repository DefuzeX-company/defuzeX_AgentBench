"""Docker image providers for the standalone model gateway service."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from agentbench.runtime.modelgateway import (
    GatewayImageProvider,
    StaticGatewayImageProvider,
)

from .image_builder import DockerBuildError, DockerImageBuilder


GATEWAY_IMAGE_ENV = "DEFUZEX_MODEL_GATEWAY_IMAGE"


@dataclass(frozen=True, slots=True)
class LocalGatewayImageProvider:
    """Build the standalone Gateway project from a source checkout."""

    builder: DockerImageBuilder
    context: Path

    def resolve_image(self) -> str:
        dockerfile = self.context / "Dockerfile"
        if not dockerfile.is_file():
            raise DockerBuildError(
                "Standalone model gateway source is unavailable. "
                f"Set {GATEWAY_IMAGE_ENV} to a published image reference."
            )
        return self.builder.build(
            context=self.context,
            dockerfile=dockerfile,
            repository="model-gateway",
        )


def default_gateway_image_provider(
    builder: DockerImageBuilder,
    environ: Mapping[str, str],
) -> GatewayImageProvider:
    """Prefer a deployed image and fall back to this checkout's service source."""

    configured_image = environ.get(GATEWAY_IMAGE_ENV, "").strip()
    if configured_image:
        return StaticGatewayImageProvider(configured_image)
    return LocalGatewayImageProvider(builder, _gateway_service_context())


def _gateway_service_context() -> Path:
    return Path(__file__).resolve().parents[3] / "services" / "model-gateway"
