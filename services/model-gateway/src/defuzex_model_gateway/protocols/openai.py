"""OpenAI-compatible gateway authentication."""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from dataclasses import dataclass

from . import GatewayAuthenticationError


@dataclass(frozen=True, slots=True)
class OpenAIProtocol:
    name: str = "openai"

    def authorize(
        self,
        path: str,
        headers: Mapping[str, str],
        *,
        gateway_token: str,
        upstream_api_key: str,
    ) -> tuple[str, dict[str, str]]:
        expected = f"Bearer {gateway_token}"
        received = _header(headers, "authorization")
        if not hmac.compare_digest(received, expected):
            raise GatewayAuthenticationError("Invalid model gateway token")
        outgoing = _copy_headers(headers, excluded={"authorization"})
        outgoing["Authorization"] = f"Bearer {upstream_api_key}"
        return path, outgoing


def _header(headers: Mapping[str, str], name: str) -> str:
    return next((value for key, value in headers.items() if key.lower() == name), "")


def _copy_headers(
    headers: Mapping[str, str], *, excluded: set[str]
) -> dict[str, str]:
    blocked = excluded | {"host", "content-length", "connection", "transfer-encoding"}
    return {key: value for key, value in headers.items() if key.lower() not in blocked}


OPENAI_PROTOCOL = OpenAIProtocol()
