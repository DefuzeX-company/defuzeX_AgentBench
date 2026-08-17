"""Model API protocol registry used by the trusted gateway."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class GatewayProtocol(Protocol):
    name: str

    def authorize(
        self,
        path: str,
        headers: Mapping[str, str],
        *,
        gateway_token: str,
        upstream_api_key: str,
    ) -> tuple[str, dict[str, str]]:
        """Validate the caller token and return upstream path and headers."""


class GatewayAuthenticationError(PermissionError):
    """Raised when a sandbox does not present its per-run gateway token."""


def get_protocol(name: str) -> GatewayProtocol:
    from .anthropic import ANTHROPIC_PROTOCOL
    from .google import GOOGLE_PROTOCOL
    from .openai import OPENAI_PROTOCOL

    protocols = {
        protocol.name: protocol
        for protocol in (OPENAI_PROTOCOL, ANTHROPIC_PROTOCOL, GOOGLE_PROTOCOL)
    }
    try:
        return protocols[name.strip().lower()]
    except KeyError as exc:
        supported = ", ".join(sorted(protocols))
        raise ValueError(
            f"Unsupported model API protocol {name!r}; supported: {supported}"
        ) from exc


__all__ = [
    "GatewayAuthenticationError",
    "GatewayProtocol",
    "get_protocol",
]
