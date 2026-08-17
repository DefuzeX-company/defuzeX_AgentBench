"""Interactive terminal client for the chat graph."""

from __future__ import annotations

from uuid import uuid4

from .graph import graph


def main() -> int:
    config = {"configurable": {"thread_id": str(uuid4())}}
    print("LangGraph chat agent. Type 'exit' to stop.")

    while True:
        try:
            prompt = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if prompt.lower() in {"exit", "quit"}:
            return 0
        if not prompt:
            continue

        try:
            result = graph.invoke({"prompt": prompt}, config=config)
        except RuntimeError as exc:
            print(f"Configuration error: {exc}")
            return 2
        print(f"Agent> {result['response']}")


if __name__ == "__main__":
    raise SystemExit(main())
