"""A deterministic adaptation of LangChain's official starter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import StateGraph


class AgentState(TypedDict):
    prompt: str
    response: str


@dataclass(frozen=True)
class RuntimeContext:
    response_prefix: str = "LangGraph starter received"


def respond(state: AgentState, runtime: object | None = None) -> dict[str, str]:
    """Build a simple response from the prompt."""
    del runtime
    prompt = state["prompt"].strip()
    response = (
        "DEFUZEX_AGENT_READY"
        if "DEFUZEX_AGENT_READY" in prompt
        else f"LangGraph starter received: {prompt}"
    )
    return {"response": response}


graph = (
    StateGraph(AgentState, context_schema=RuntimeContext)
    .add_node("respond", respond)
    .add_edge("__start__", "respond")
    .compile(name="DefuzeX LangGraph New Project Starter")
)

