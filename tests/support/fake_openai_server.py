"""Small OpenAI-compatible endpoint used by the Docker integration smoke test."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length)) if length else {}
        if self.headers.get("Authorization") != "Bearer integration-test-key":
            self.send_error(401)
            return
        body = json.dumps(_completion(request)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _completion(request: dict[str, object]) -> dict[str, object]:
    response_format = request.get("response_format")
    messages = request.get("messages", [])
    tool_names = {
        str(item.get("function", {}).get("name", ""))
        for item in request.get("tools", [])
        if isinstance(item, dict) and isinstance(item.get("function"), dict)
    }
    if isinstance(response_format, dict):
        message: dict[str, object] = {
            "role": "assistant",
            "content": json.dumps(
                {
                    "reasoning": "The sender asks a direct question.",
                    "classification": "respond",
                }
            ),
        }
        finish_reason = "stop"
    elif "RouterSchema" in tool_names:
        message = _tool_call(
            "RouterSchema",
            {
                "reasoning": "The sender asks a direct question.",
                "classification": "respond",
            },
            "call-router",
        )
        finish_reason = "tool_calls"
    elif isinstance(messages, list) and any(
        isinstance(item, dict) and item.get("role") == "tool" for item in messages
    ):
        message = _tool_call("Done", {"done": True}, "call-done")
        finish_reason = "tool_calls"
    elif request.get("tools"):
        message = _tool_call(
            "write_email",
            {
                "to": "alex@example.com",
                "subject": "Re: API documentation question",
                "content": "I will confirm the documentation timeline by Friday.",
            },
            "call-write-email",
        )
        finish_reason = "tool_calls"
    else:
        message = {
            "role": "assistant",
            "content": "Hello from the isolated chat agent.",
        }
        finish_reason = "stop"

    return {
        "id": "chatcmpl-defuzex-smoke",
        "object": "chat.completion",
        "created": 0,
        "model": str(request.get("model", "gpt-4.1-mini")),
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        },
    }


def _tool_call(name: str, arguments: dict[str, object], call_id: str) -> dict[str, object]:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments),
                },
            }
        ],
    }


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
