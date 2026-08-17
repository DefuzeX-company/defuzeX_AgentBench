"""Google-native gateway authentication."""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from . import GatewayAuthenticationError
from .openai import _copy_headers, _header


@dataclass(frozen=True, slots=True)
class GoogleProtocol:
    name: str = "google"

    def authorize(
        self,
        path: str,
        headers: Mapping[str, str],
        *,
        gateway_token: str,
        upstream_api_key: str,
    ) -> tuple[str, dict[str, str]]:
        parsed = urlsplit(path)
        query = parse_qsl(parsed.query, keep_blank_values=True)
        query_token = next((value for key, value in query if key == "key"), "")
        header_token = _header(headers, "x-goog-api-key")
        received = header_token or query_token
        if not hmac.compare_digest(received, gateway_token):
            raise GatewayAuthenticationError("Invalid model gateway token")

        outgoing = _copy_headers(headers, excluded={"x-goog-api-key"})
        cleaned_query = [(key, value) for key, value in query if key != "key"]
        cleaned_query.append(("key", upstream_api_key))
        upstream_path = urlunsplit(
            ("", "", parsed.path, urlencode(cleaned_query), parsed.fragment)
        )
        return upstream_path, outgoing


GOOGLE_PROTOCOL = GoogleProtocol()
