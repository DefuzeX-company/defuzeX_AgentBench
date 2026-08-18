"""Trusted model API protocol registry."""

from __future__ import annotations

from collections.abc import Mapping
from importlib.metadata import entry_points
from typing import Protocol


ENTRY_POINT_GROUP = "defuzex.model_gateway.protocols"


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


class ProtocolRegistry:
    """Registry of trusted, same-protocol credential adapters."""

    def __init__(self) -> None:
        self._protocols: dict[str, GatewayProtocol] = {}

    def register(self, protocol: GatewayProtocol) -> None:
        name = getattr(protocol, "name", "").strip().lower()
        if not name or not callable(getattr(protocol, "authorize", None)):
            raise TypeError("Gateway protocol must define name and authorize()")
        if name in self._protocols:
            raise ValueError(f"Gateway protocol is already registered: {name}")
        self._protocols[name] = protocol

    def get(self, name: str) -> GatewayProtocol:
        normalized = name.strip().lower()
        try:
            return self._protocols[normalized]
        except KeyError as exc:
            supported = ", ".join(sorted(self._protocols))
            raise ValueError(
                f"Unsupported model API protocol {name!r}; supported: {supported}"
            ) from exc


def create_protocol_registry(*, include_plugins: bool = True) -> ProtocolRegistry:
    from .anthropic import ANTHROPIC_PROTOCOL
    from .google import GOOGLE_PROTOCOL
    from .openai import OPENAI_PROTOCOL

    registry = ProtocolRegistry()
    for protocol in (OPENAI_PROTOCOL, ANTHROPIC_PROTOCOL, GOOGLE_PROTOCOL):
        registry.register(protocol)
    if include_plugins:
        for entry_point in entry_points(group=ENTRY_POINT_GROUP):
            if entry_point.dist and entry_point.dist.name == "defuzex-model-gateway":
                continue
            loaded = entry_point.load()
            protocol = loaded() if callable(loaded) and not hasattr(loaded, "authorize") else loaded
            registry.register(protocol)
    return registry


_DEFAULT_REGISTRY: ProtocolRegistry | None = None


def get_protocol(name: str) -> GatewayProtocol:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = create_protocol_registry()
    return _DEFAULT_REGISTRY.get(name)


__all__ = [
    "GatewayAuthenticationError",
    "GatewayProtocol",
    "ProtocolRegistry",
    "create_protocol_registry",
    "get_protocol",
]
