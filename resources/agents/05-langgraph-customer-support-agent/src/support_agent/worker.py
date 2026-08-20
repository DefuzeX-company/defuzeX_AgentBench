"""AgentBench JSONL transport for the customer support graph."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from contextlib import redirect_stdout
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from benchmark_mocks import get_mock_service, reset_mock_service
from support_agent.agent import graph


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

        reset_mock_service()
        graph_input = _graph_input(request["input"])
        with redirect_stdout(sys.stderr):
            result = graph.invoke(graph_input, config=request.get("run_config"))

        output = _public_output(result)
        return {
            "ok": True,
            "output": output,
            "raw_output": {
                **output,
                "message_count": len(result.get("messages", [])),
                "mock_trace": get_mock_service().get_trace_as_dicts(),
            },
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _graph_input(value: object) -> dict[str, object]:
    if isinstance(value, str):
        content = value.strip()
        if not content:
            raise ValueError("Customer support input must not be empty")
        return {"messages": [HumanMessage(content=content)]}

    if not isinstance(value, Mapping):
        raise ValueError("Customer support input must be text or a JSON object")

    if "messages" in value:
        messages = value["messages"]
        if not isinstance(messages, Sequence) or isinstance(messages, (str, bytes)):
            raise ValueError("'messages' must be a JSON array")
        return {"messages": [_message_from_json(item) for item in messages]}

    for key in ("message", "prompt", "customer_message"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return {"messages": [HumanMessage(content=candidate.strip())]}

    raise ValueError(
        "Customer support object input must contain 'messages', 'message', "
        "'prompt', or 'customer_message'"
    )


def _message_from_json(value: object) -> BaseMessage:
    if isinstance(value, str):
        return HumanMessage(content=value)
    if not isinstance(value, Mapping):
        raise ValueError("Each message must be text or a JSON object")

    role = str(value.get("role", "user")).lower()
    content = value.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Each message object must contain non-empty string content")
    if role in {"assistant", "ai"}:
        return AIMessage(content=content)
    if role in {"user", "human"}:
        return HumanMessage(content=content)
    raise ValueError(f"Unsupported message role: {role}")


def _public_output(result: Mapping[str, Any]) -> dict[str, object]:
    messages = list(result.get("messages", []))
    final_response = ""
    actions: list[dict[str, object]] = []

    for message in messages:
        content = getattr(message, "content", "")
        if isinstance(message, AIMessage) and isinstance(content, str) and content.strip():
            final_response = content.strip()
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
        "final_response": final_response,
        "actions": actions,
        "mock_operations": get_mock_service().get_trace_as_dicts(),
    }


def _json_value(value: object) -> object:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
