from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from benchmark_mocks.harness import run_benchmark_task


class BenchmarkState(TypedDict, total=False):
    scenario: str
    work_dir: str
    case_prompt: str
    result: dict[str, Any]
    summary: str


def prepare_task(state: BenchmarkState) -> BenchmarkState:
    scenario = state.get("scenario") or "default"
    return {
        "scenario": scenario,
        "work_dir": state.get("work_dir", ""),
        "case_prompt": state.get("case_prompt", ""),
    }


def run_swe_agent(state: BenchmarkState) -> BenchmarkState:
    result = run_benchmark_task(
        scenario=state.get("scenario") or "default",
        work_dir=state.get("work_dir") or None,
    )
    return {"result": result}


def summarize_result(state: BenchmarkState) -> BenchmarkState:
    result = state["result"]
    summary = (
        f"SWE-agent benchmark {result['status']}: "
        f"exit_status={result.get('exit_status')}, "
        f"trajectory_steps={result.get('trajectory_steps')}, "
        f"validation={result.get('validation_command')}"
    )
    return {"summary": summary}


builder = StateGraph(BenchmarkState)
builder.add_node("prepare_task", prepare_task)
builder.add_node("run_swe_agent", run_swe_agent)
builder.add_node("summarize_result", summarize_result)
builder.add_edge(START, "prepare_task")
builder.add_edge("prepare_task", "run_swe_agent")
builder.add_edge("run_swe_agent", "summarize_result")
builder.add_edge("summarize_result", END)

graph = builder.compile()
