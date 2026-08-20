"""AgentBench JSONL transport for the SWE-agent benchmark graph."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from contextlib import redirect_stdout
from typing import Any


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
        with redirect_stdout(sys.stderr):
            from .graph import graph

            result = graph.invoke(graph_input, config=request.get("run_config"))

        output = _public_output(result)
        return {
            "ok": True,
            "output": output,
            "raw_output": {
                **output,
                "mock_trace": _json_value(result.get("result", {}).get("mock_trace", [])),
                "validation_output": _tail(result.get("result", {}).get("validation_output", "")),
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _graph_input(value: object) -> dict[str, object]:
    if isinstance(value, str):
        if not value.strip():
            raise ValueError("SWE-agent benchmark text input must not be empty")
        return {"scenario": "default", "case_prompt": value.strip()}

    if not isinstance(value, Mapping):
        raise ValueError("SWE-agent benchmark input must be text or a JSON object")

    scenario = value.get("scenario", "default")
    if not isinstance(scenario, str) or not scenario.strip():
        raise ValueError("'scenario' must be a non-empty string")

    graph_input: dict[str, object] = {"scenario": scenario.strip()}
    case_prompt = value.get("case_prompt") or value.get("prompt") or value.get("task")
    if isinstance(case_prompt, str):
        graph_input["case_prompt"] = case_prompt
    work_dir = value.get("work_dir")
    if isinstance(work_dir, str) and work_dir.strip():
        graph_input["work_dir"] = work_dir
    return graph_input


def _public_output(result: Mapping[str, Any]) -> dict[str, object]:
    raw = result.get("result", {})
    if not isinstance(raw, Mapping):
        raise ValueError("SWE-agent graph did not return a result object")

    validation_exit_code = raw.get("validation_exit_code")
    return {
        "status": str(raw.get("status", "unknown")),
        "problem_id": str(raw.get("problem_id", "")),
        "summary": str(result.get("summary", "")),
        "validation_command": str(raw.get("validation_command", "")),
        "validation_exit_code": validation_exit_code,
        "validation_passed": validation_exit_code == 0,
        "diff": str(raw.get("diff", "")),
        "submission": str(raw.get("submission", "") or ""),
        "exit_status": str(raw.get("exit_status", "") or ""),
        "trajectory_steps": raw.get("trajectory_steps", 0),
    }


def _tail(value: object, limit: int = 4000) -> str:
    text = str(value or "")
    return text[-limit:]


def _json_value(value: object) -> object:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
