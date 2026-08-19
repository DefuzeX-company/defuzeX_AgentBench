"""Local result viewer server for AgentBench JSONL artifacts."""

from __future__ import annotations

import json
import threading
from argparse import ArgumentParser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Sequence
from urllib.parse import unquote, urlparse

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


@dataclass(frozen=True)
class RunningViewer:
    """Background local viewer server."""

    server: ThreadingHTTPServer
    thread: threading.Thread
    url: str

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def view_cli(argv: Sequence[str] | None = None) -> int:
    """Run the local result viewer server."""

    parser = ArgumentParser(
        prog="agentbench view",
        description="Serve a local AgentBench result viewer.",
    )
    parser.add_argument("result_log", help="Path to an AgentBench .jsonl result log.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)

    serve_result_log(args.result_log, host=args.host, port=args.port)
    return 0


def serve_result_log(
    result_log: str | Path,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    """Serve the static viewer and result-log API until interrupted."""

    path = Path(result_log).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Result log not found: {path}")

    server = create_viewer_server(path, host=host, port=port)
    url = f"http://{host}:{server.server_port}"
    print(f"View: {url}")
    print(f"Result log: {path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nViewer stopped.")
    finally:
        server.server_close()


def start_viewer_server(
    result_log: str | Path,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> RunningViewer:
    """Start the result viewer in a daemon thread."""

    server = create_viewer_server(Path(result_log).resolve(), host=host, port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return RunningViewer(
        server=server,
        thread=thread,
        url=f"http://{host}:{server.server_port}",
    )


def create_viewer_server(
    result_log: Path,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> ThreadingHTTPServer:
    """Create a local viewer server, falling back to a free port if needed."""

    handler = build_viewer_handler(result_log)
    try:
        return ThreadingHTTPServer((host, port), handler)
    except OSError:
        if port == 0:
            raise
        return ThreadingHTTPServer((host, 0), handler)


def build_viewer_handler(result_log: Path) -> type[SimpleHTTPRequestHandler]:
    """Build a request handler bound to one JSONL result artifact."""

    class ViewerHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/result":
                self._send_json(parse_result_log(result_log))
                return
            if parsed.path == "/api/health":
                self._send_json({"ok": True})
                return

            self.path = _static_path(parsed.path)
            super().do_GET()

        def _send_json(self, payload: object) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return ViewerHandler


def parse_result_log(path: str | Path) -> dict[str, object]:
    """Parse a JSONL result log into the shape consumed by the viewer."""

    result_path = Path(path)
    events: list[dict[str, object]] = []
    parse_errors: list[dict[str, object]] = []

    for line_number, line in enumerate(
        result_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            parse_errors.append({"line": line_number, "message": exc.msg})
            continue
        if isinstance(event, dict):
            events.append(event)
        else:
            parse_errors.append(
                {"line": line_number, "message": "Expected JSON object"}
            )

    selected_agent_ids: list[str] = []
    agents: list[dict[str, object]] = []
    step_events_by_agent: dict[str, list[dict[str, object]]] = {}
    summary: dict[str, object] | None = None
    suite_error: dict[str, object] | None = None

    for event in events:
        event_type = event.get("event")
        if event_type == "run_started":
            selected = event.get("selected_agent_ids")
            if isinstance(selected, list):
                selected_agent_ids = [str(agent_id) for agent_id in selected]
        elif event_type == "agent_completed":
            item = event.get("item")
            if isinstance(item, dict):
                agents.append(item)
        elif event_type in {"step_started", "step_completed", "step_failed"}:
            agent_id = event.get("agent_id")
            if isinstance(agent_id, str):
                step_events_by_agent.setdefault(agent_id, []).append(event)
        elif event_type == "suite_completed":
            event_summary = event.get("summary")
            if isinstance(event_summary, dict):
                summary = event_summary
        elif event_type == "suite_failed":
            error = event.get("error")
            if isinstance(error, dict):
                suite_error = error

    state = "complete" if summary is not None else "running_or_interrupted"
    if suite_error is not None:
        state = "failed"

    agents = _merge_step_events(agents, step_events_by_agent)

    return {
        "path": str(result_path),
        "state": state,
        "selected_agent_ids": selected_agent_ids,
        "agents": agents,
        "summary": summary,
        "suite_error": suite_error,
        "parse_errors": parse_errors,
        "event_count": len(events),
    }


def _merge_step_events(
    agents: list[dict[str, object]],
    step_events_by_agent: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen: set[str] = set()

    for item in agents:
        agent_id = item.get("agent_id")
        if isinstance(agent_id, str):
            item = dict(item)
            item["step_events"] = step_events_by_agent.get(agent_id, [])
            seen.add(agent_id)
        merged.append(item)

    for agent_id, step_events in step_events_by_agent.items():
        if agent_id in seen:
            continue
        merged.append(
            {
                "agent_id": agent_id,
                "benchmark": None,
                "error": {
                    "type": "Incomplete",
                    "message": "Agent did not produce a final suite result.",
                },
                "step_events": step_events,
            }
        )

    return merged


def _static_path(path: str) -> str:
    static_path = unquote(path)
    if static_path in {"", "/"}:
        return "/index.html"
    return static_path
