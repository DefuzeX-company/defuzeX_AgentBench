"""Image resolution contract for trusted model gateway deployments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class GatewayImageProvider(Protocol):
    """Resolve a runnable model gateway image reference."""

    def resolve_image(self) -> str:
        """Return a local tag or registry image reference."""


@dataclass(frozen=True, slots=True)
class StaticGatewayImageProvider:
    """Use an immutable image supplied by a release or deployment environment."""

    image: str

    def __post_init__(self) -> None:
        if not self.image.strip():
            raise ValueError("Gateway image reference cannot be empty")

    def resolve_image(self) -> str:
        return self.image
