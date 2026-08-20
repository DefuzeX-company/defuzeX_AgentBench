# SWE-agent Local Bug-Fix Benchmark

This AgentBench adapter vendors the SWE-agent runtime and exposes one selected
LangGraph graph through a persistent JSONL worker.

The benchmark task prepares a deterministic local Python repository with a
boundary-condition bug in `range_utils.ranges_overlap`. SWE-agent must inspect
the repository, edit source code, run the validation command, and submit the
resulting patch. The adapter keeps SWE-agent's normal action/observation loop
through `DefaultAgent.run(...)`.

## AgentBench Runtime

- Graph: `swe_agent_benchmark` in `src/swe_agent_benchmark/graph.py`
- Worker: `python -m swe_agent_benchmark.worker`
- Input mode: persistent JSONL over stdin
- Output mode: one JSON object per input line on stdout
- Model protocol: OpenAI-compatible
- Writable runtime paths: `/tmp/agentbench-workspaces`,
  `/tmp/agentbench-home`, and `/run/agentbench-tools`

The Docker image runs as uid `10001`. Upstream SWE-agent paths that normally
write under `/root` are redirected through `SWE_AGENT_RUNTIME_HOME`,
`SWE_AGENT_TOOLS_ROOT`, and `SWE_AGENT_MODEL_PATCH`.

## Input

Official DefuzeX Cases may provide plain text. The worker treats text as a
benchmark prompt and runs the default local fixture scenario:

```json
{"input": "Fix the local range overlap bug."}
```

Custom Cases may provide:

```json
{
  "input": {
    "scenario": "default",
    "case_prompt": "Fix the local range overlap bug."
  }
}
```

Only the `default` scenario is currently supported.

## Output

The public result is JSON-compatible and includes:

- `status`
- `problem_id`
- `summary`
- `validation_command`
- `validation_exit_code`
- `validation_passed`
- `diff`
- `submission`
- `exit_status`
- `trajectory_steps`

`raw_output` also contains a safe mock trace and truncated validation output for
local debugging. It must not contain credentials or environment dumps.

## Local Smoke

From this directory:

```powershell
docker build -t agentbench-swe-agent .
```

AgentBench should launch the worker through `agent.toml`; direct local Python
execution requires Python 3.11 and the package dependencies.
