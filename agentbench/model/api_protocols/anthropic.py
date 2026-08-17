"""Anthropic-native gateway authentication."""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from dataclasses import dataclass

from . import GatewayAuthenticationError
from .openai import _copy_headers, _header


@dataclass(frozen=True, slots=True)
class AnthropicProtocol:
    name: str = "anthropic"

    def authorize(
        self,
        path: str,
        headers: Mapping[str, str],
        *,
        gateway_token: str,
        upstream_api_key: str,
    ) -> tuple[str, dict[str, str]]:
        received = _header(headers, "x-api-key")
        if not hmac.compare_digest(received, gateway_token):
            raise GatewayAuthenticationError("Invalid model gateway token")
        outgoing = _copy_headers(headers, excluded={"x-api-key"})
        outgoing["x-api-key"] = upstream_api_key
        return path, outgoing


ANTHROPIC_PROTOCOL = AnthropicProtocol()
