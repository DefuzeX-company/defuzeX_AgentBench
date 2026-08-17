"""AgentBench JSONL transport for the basic email assistant graph."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from contextlib import redirect_stdout
from typing import Any

from .email_assistant import email_assistant


EMAIL_FIELDS = frozenset({"author", "to", "subject", "email_thread"})


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        response = _handle(line)
        print(json.dumps(response, ensure_ascii=False), flush=True)
    return 0


def _handle(line: str) -> dict[str, object]:
    try:
        request = json.loads(line)
        if not isinstance(request, dict) or "input" not in request:
            raise ValueError("JSONL request must contain 'input'")

        graph_input = _graph_input(request["input"])
        # The upstream graph prints triage diagnostics. Stdout is reserved for
        # the JSONL response contract, so diagnostics belong on stderr.
        with redirect_stdout(sys.stderr):
            result = email_assistant.invoke(
                graph_input,
                config=request.get("run_config"),
            )

        output = _public_output(result)
        return {
            "ok": True,
            "output": output,
            "raw_output": {
                **output,
                "message_count": len(result.get("messages", [])),
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _graph_input(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("Email assistant input must be a JSON object")

    if "email_input" in value:
        email_input = value["email_input"]
        if not isinstance(email_input, Mapping):
            raise ValueError("'email_input' must be a JSON object")
        graph_input = dict(value)
    else:
        email_input = value
        graph_input = {"email_input": dict(value)}

    missing = sorted(EMAIL_FIELDS.difference(email_input))
    if missing:
        raise ValueError(f"Email input is missing fields: {', '.join(missing)}")
    return graph_input


def _public_output(result: Mapping[str, Any]) -> dict[str, object]:
    classification = result.get("classification_decision")
    actions: list[dict[str, object]] = []
    for message in result.get("messages", []):
        for call in getattr(message, "tool_calls", ()) or ():
            if not isinstance(call, Mapping):
                continue
            actions.append(
                {
                    "name": str(call.get("name", "")),
                    "arguments": _json_value(call.get("args", {})),
                }
            )
    return {
        "classification": classification,
        "actions": actions,
    }


def _json_value(value: object) -> object:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
