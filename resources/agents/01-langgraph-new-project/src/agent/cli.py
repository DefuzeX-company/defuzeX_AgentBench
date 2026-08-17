from __future__ import annotations

import json
import sys

from .graph import graph


def main() -> int:
    """Read stdin, run graph, and print JSON."""
    prompt = sys.stdin.read().strip()
    if not prompt:
        print("stdin prompt is required", file=sys.stderr)
        return 2
    result = graph.invoke({"prompt": prompt})
    print(
        json.dumps(
            {
                "response": result["response"],
                "graph": "DefuzeX LangGraph New Project Starter",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

