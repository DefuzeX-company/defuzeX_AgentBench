"""HTTP gateway that keeps upstream credentials out of Agent containers."""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .protocols import GatewayAuthenticationError, GatewayProtocol, get_protocol


MAX_REQUEST_BYTES = 16 * 1024 * 1024
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class GatewayServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        protocol: GatewayProtocol,
        upstream_base_url: str,
        gateway_token: str,
        upstream_api_key: str,
    ) -> None:
        super().__init__(address, GatewayRequestHandler)
        self.protocol = protocol
        self.upstream_base_url = upstream_base_url.rstrip("/") + "/"
        self.gateway_token = gateway_token
        self.upstream_api_key = upstream_api_key


class GatewayRequestHandler(BaseHTTPRequestHandler):
    server: GatewayServer

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write(200, b'{"status":"ok"}', {"Content-Type": "application/json"})
            return
        self._proxy()

    def do_POST(self) -> None:  # noqa: N802
        self._proxy()

    def do_DELETE(self) -> None:  # noqa: N802
        self._proxy()

    def do_PATCH(self) -> None:  # noqa: N802
        self._proxy()

    def do_PUT(self) -> None:  # noqa: N802
        self._proxy()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _proxy(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._write(400, b"Invalid Content-Length")
            return
        if length < 0 or length > MAX_REQUEST_BYTES:
            self._write(413, b"Request body is too large")
            return

        try:
            path, headers = self.server.protocol.authorize(
                self.path,
                dict(self.headers.items()),
                gateway_token=self.server.gateway_token,
                upstream_api_key=self.server.upstream_api_key,
            )
        except GatewayAuthenticationError:
            self._write(401, b"Unauthorized")
            return

        parsed_path = urlsplit(path)
        if parsed_path.scheme or parsed_path.netloc or not parsed_path.path.startswith("/"):
            self._write(400, b"Invalid upstream path")
            return
        body = self.rfile.read(length) if length else None
        target = _upstream_url(self.server.upstream_base_url, path)
        request = Request(target, data=body, headers=headers, method=self.command)
        try:
            with urlopen(request, timeout=300) as response:
                self._write(response.status, response.read(), dict(response.headers.items()))
        except HTTPError as exc:
            self._write(exc.code, exc.read(), dict(exc.headers.items()))
        except URLError:
            self._write(502, b"Model provider is unavailable")

    def _write(
        self,
        status: int,
        body: bytes,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        for key, value in (headers or {}).items():
            if key.lower() not in HOP_BY_HOP_HEADERS | {"content-length"}:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    protocol = get_protocol(_required_env("DEFUZEX_GATEWAY_PROTOCOL"))
    server = GatewayServer(
        ("0.0.0.0", int(os.environ.get("DEFUZEX_GATEWAY_PORT", "8080"))),
        protocol=protocol,
        upstream_base_url=_required_env("DEFUZEX_GATEWAY_UPSTREAM"),
        gateway_token=_read_secret("DEFUZEX_GATEWAY_TOKEN_FILE"),
        upstream_api_key=_read_secret("DEFUZEX_GATEWAY_UPSTREAM_KEY_FILE"),
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required gateway setting is missing: {name}")
    return value


def _read_secret(env_name: str) -> str:
    path = Path(_required_env(env_name))
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"Gateway secret file is empty: {env_name}")
    return value


def _upstream_url(base_url: str, request_path: str) -> str:
    base = urlsplit(base_url)
    request = urlsplit(request_path)
    base_path = base.path.rstrip("/")
    if base_path and (
        request.path == base_path or request.path.startswith(base_path + "/")
    ):
        path = request.path
    else:
        path = f"{base_path}/{request.path.lstrip('/')}"
    return urlunsplit((base.scheme, base.netloc, path, request.query, ""))


if __name__ == "__main__":
    raise SystemExit(main())
