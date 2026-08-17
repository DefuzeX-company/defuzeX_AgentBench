"""JSONL transport used by AgentBench inside the isolated container."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping

from .graph import graph


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
        value = request["input"]
        graph_input = value if isinstance(value, Mapping) else {"prompt": value}
        result = graph.invoke(graph_input, config=request.get("run_config"))
        output = result["response"]
        return {
            "ok": True,
            "output": output,
            "raw_output": {
                "response": output,
                "message_count": len(result.get("messages", [])),
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


if __name__ == "__main__":
    raise SystemExit(main())
