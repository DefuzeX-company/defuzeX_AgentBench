#!/usr/bin/env python
"""Non-interactive smoke and e2e runner for AgentBench."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark_mocks import get_mock_service, reset_mock_service  # noqa: E402
from src.support_agent.agent import graph  # noqa: E402
from src.support_agent.model_factory import (  # noqa: E402
    ModelConfigurationError,
    get_model_config,
)


EXPECTED_TASK = (
    "I'm really frustrated. Order #123456 arrived defective. Check my order, "
    "explain the return policy, start a return, and escalate if needed."
)

REQUIRED_OPERATIONS = {
    ("orders", "get_order_status"),
    ("knowledge_base", "search"),
    ("returns", "initiate_return"),
    ("helpdesk", "escalate_to_human"),
}


def run(message: str) -> int:
    try:
        get_model_config()
    except ModelConfigurationError as exc:
        print(f"LLM configuration error: {exc}", file=sys.stderr)
        return 10

    service = reset_mock_service()
    result = graph.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": "agentbench-smoke"}},
    )

    final_message = result["messages"][-1]
    trace = get_mock_service().get_trace_as_dicts()
    observed = {(entry["service"], entry["operation"]) for entry in trace}
    missing = sorted(REQUIRED_OPERATIONS - observed)

    print("FINAL_RESPONSE_START")
    print(final_message.content)
    print("FINAL_RESPONSE_END")
    print("MOCK_TRACE_START")
    print(json.dumps(trace, indent=2))
    print("MOCK_TRACE_END")

    if missing:
        print(f"Missing required mock operations: {missing}", file=sys.stderr)
        return 2

    if not final_message.content:
        print("Final response was empty", file=sys.stderr)
        return 3

    if not service.get_trace():
        print("Mock trace was empty", file=sys.stderr)
        return 4

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", default=EXPECTED_TASK)
    args = parser.parse_args()
    return run(args.message)


if __name__ == "__main__":
    raise SystemExit(main())
