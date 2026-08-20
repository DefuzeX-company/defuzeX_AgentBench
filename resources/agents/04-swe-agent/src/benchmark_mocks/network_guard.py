from __future__ import annotations

import os
import socket
from contextlib import contextmanager
from urllib.parse import urlparse


ALLOWED_HOST_SUFFIXES = (
    ".openai.com",
    ".azure.com",
    ".azureapi.net",
    ".anthropic.com",
)


def _is_allowed_host(host: str | None) -> bool:
    if not host:
        return False
    host = host.lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    return any(host.endswith(suffix) or host == suffix.removeprefix(".") for suffix in ALLOWED_HOST_SUFFIXES)


@contextmanager
def block_non_llm_network():
    """Block raw socket connections except known LLM endpoints.

    This is a best-effort guard for Python-level networking. The benchmark
    configuration also avoids external git, browser, GitHub, and HF paths.
    """
    if os.getenv("AGENTBENCH_DISABLE_NETWORK_GUARD") == "1":
        yield
        return

    original_connect = socket.socket.connect
    original_getaddrinfo = socket.getaddrinfo
    allowed_addresses: set[str] = set()

    def guarded_getaddrinfo(host, port, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = original_getaddrinfo(host, port, *args, **kwargs)
        if isinstance(host, str) and _is_allowed_host(host):
            for item in result:
                sockaddr = item[4]
                if sockaddr:
                    allowed_addresses.add(str(sockaddr[0]))
        return result

    def guarded_connect(self, address):  # type: ignore[no-untyped-def]
        host = address[0] if isinstance(address, tuple) and address else None
        normalized_host = str(host) if host else None
        if not _is_allowed_host(normalized_host) and normalized_host not in allowed_addresses:
            raise RuntimeError(f"Blocked non-LLM network access to {address!r}")
        return original_connect(self, address)

    socket.getaddrinfo = guarded_getaddrinfo  # type: ignore[assignment]
    socket.socket.connect = guarded_connect  # type: ignore[method-assign]
    try:
        yield
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]


def assert_url_allowed(url: str) -> None:
    parsed = urlparse(url)
    if not _is_allowed_host(parsed.hostname):
        raise RuntimeError(f"Blocked non-LLM URL: {url}")
