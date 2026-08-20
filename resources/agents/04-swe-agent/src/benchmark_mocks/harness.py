from __future__ import annotations

import os
import shlex
import tempfile
from pathlib import Path
from typing import Any

import yaml

from benchmark_mocks.local_env import LocalBenchmarkEnv
from benchmark_mocks.network_guard import block_non_llm_network
from benchmark_mocks.task import BenchmarkTask, prepare_fixture
from benchmark_mocks.trace import MockTrace, load_trace
from sweagent import CONFIG_DIR
from sweagent.agent.agents import DefaultAgent, DefaultAgentConfig
from sweagent.agent.problem_statement import TextProblemStatement


def _require_openai_key() -> None:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider != "openai":
        raise RuntimeError(f"Unsupported provider for this benchmark: {provider}. Set LLM_PROVIDER=openai.")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required before running the SWE-agent benchmark.")


def _build_agent() -> DefaultAgent:
    config_path = CONFIG_DIR / "agentbench.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    agent_data = data["agent"]
    agent_data["model"] = {
        "name": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "api_key": "$OPENAI_API_KEY",
        "api_base": os.getenv("OPENAI_BASE_URL") or None,
        "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0")),
        "per_instance_cost_limit": float(os.getenv("AGENTBENCH_COST_LIMIT", "3.0")),
        "per_instance_call_limit": int(os.getenv("AGENTBENCH_CALL_LIMIT", "20")),
        "retry": {"retries": 2, "min_wait": 1, "max_wait": 5},
        "max_input_tokens": int(os.getenv("AGENTBENCH_MAX_INPUT_TOKENS", "0")),
        "max_output_tokens": int(os.getenv("AGENTBENCH_MAX_OUTPUT_TOKENS", "4096")),
        "fallbacks": [],
    }
    config = DefaultAgentConfig.model_validate(agent_data)
    return DefaultAgent.from_config(config)


def run_benchmark_task(scenario: str = "default", work_dir: str | None = None) -> dict[str, Any]:
    _require_openai_key()
    with tempfile.TemporaryDirectory(prefix="swe-agent-benchmark-") as tmp:
        base = Path(work_dir) if work_dir else Path(tmp)
        base.mkdir(parents=True, exist_ok=True)
        task = prepare_fixture(base, scenario=scenario)
        result = _run_agent(task=task, output_dir=base / "trajectories")
        result["mock_trace"] = load_trace(task.trace_path)
        return result


def _run_agent(task: BenchmarkTask, output_dir: Path) -> dict[str, Any]:
    trace = MockTrace(task.trace_path)
    env = LocalBenchmarkEnv(task.repo_path, trace)
    problem = TextProblemStatement(text=task.problem_statement, id="agentbench-range-utils")
    agent = _build_agent()
    output_dir.mkdir(parents=True, exist_ok=True)
    with block_non_llm_network():
        run_result = agent.run(env=env, problem_statement=problem, output_dir=output_dir)
    fixture_cwd = shlex.quote(str(env.cwd))
    validation_result = env._run_shell(
        f"cd {fixture_cwd} && {task.validation_command}",
        cwd=env.cwd,
        timeout=60,
        update_cwd=False,
    )
    validation = validation_result.output
    diff = env.communicate(f"cd {fixture_cwd} && git diff -- src/range_utils/ranges.py", timeout=30, check="ignore")
    trace.record(
        "fixture_repo",
        "verify",
        "Ran validation command",
        exit_code=validation_result.exit_code,
        output=validation[-2000:],
    )
    env.close()
    return {
        "status": "passed" if validation_result.exit_code == 0 else "failed",
        "problem_id": problem.id,
        "repo": str(task.repo_path),
        "validation_command": task.validation_command,
        "validation_exit_code": validation_result.exit_code,
        "validation_output": validation,
        "diff": diff,
        "submission": run_result.info.get("submission"),
        "exit_status": run_result.info.get("exit_status"),
        "trajectory_steps": len(run_result.trajectory),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_benchmark_task(), indent=2))
