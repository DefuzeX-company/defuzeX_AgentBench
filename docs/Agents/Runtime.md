# Runtime Contract

This page covers the details that most often break Agent onboarding: Docker
filesystem layout, Python packaging, JSONL workers, and model Gateway wiring.

## Docker Filesystem

AgentBench runs Agent containers with a read-only root filesystem, no public
egress, dropped Linux capabilities, and fresh tmpfs mounts.

| Path | Runtime behavior | Use |
| --- | --- | --- |
| `/opt/agent` | image content, read-only at runtime | installed Agent project, config, static files, vendored tools |
| `/tmp` | writable tmpfs with `noexec` | workspaces, state, logs, non-executable temporary data |
| `/run/agentbench-tools` | writable executable tmpfs | uploaded tool bundles with executable `bin/*` |

Never fix a tool execution problem by making all of `/tmp` executable. Put
executable uploaded tools under `/run/agentbench-tools`.

## Dockerfile Rules

Use a non-root image and let `agent.toml` own the launch command:

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/agent
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 agent

USER agent
```

Do not set `ENTRYPOINT` unless the runtime contract is changed.

For Agents with project-relative config paths:

```dockerfile
ENV MY_AGENT_CONFIG_DIR=/opt/agent/config
ENV SWE_AGENT_CONFIG_ROOT=/opt/agent
```

For Agents that upload executable tools:

```dockerfile
ENV SWE_AGENT_TOOLS_ROOT=/run/agentbench-tools
```

## Installed Package Versus Source Tree

After `pip install .`, imported code lives under `site-packages`. This is a
common bug:

```python
repo_root = Path(__file__).resolve().parents[2]
config_path = repo_root / "config" / "agentbench.yaml"
```

Use explicit runtime paths instead:

```python
CONFIG_DIR = Path(os.getenv("MY_AGENT_CONFIG_DIR", "/opt/agent/config"))
config_path = CONFIG_DIR / "agentbench.yaml"
```

If runtime code needs fixtures, prompts, schemas, or templates, include them in
the wheel or image. For setuptools:

```toml
[tool.setuptools]
package-dir = {"" = "src"}
include-package-data = true

[tool.setuptools.packages.find]
where = ["src"]
include = ["my_agent*", "benchmark_mocks*"]

[tool.setuptools.package-data]
benchmark_mocks = [
    "fixtures/example_repo/README.md",
    "fixtures/example_repo/pyproject.toml",
    "fixtures/example_repo/src/example/__init__.py",
    "fixtures/example_repo/tests/test_example.py",
]
```

Add a test that every declared package-data file exists.

## JSONL Worker

The container must run a persistent stdin/stdout worker:

```text
stdin:  {"input": <SDK payload>, "run_config": <optional object>}\n
stdout: {"ok": true, "output": <public result>, "raw_output": <diagnostic>}\n
stdout: {"ok": false, "error": "ErrorType: safe message"}\n
```

Rules:

- Keep stdout as JSONL only; send logs to stderr.
- Handle multiple input lines in one process.
- Accept text and structured JSON-compatible inputs.
- Pass `run_config` to LangGraph when thread state is used.
- Normalize output to stable public behavior, not raw LangChain objects.
- Keep `raw_output` safe and serializable.

## Model Gateway

Model credentials belong to `[model]`, not `runtime.secret_env_keys`. The Agent
container receives a temporary Gateway token through the Agent-facing variables
declared in `agent.toml`.

For OpenAI-compatible Agents:

```toml
[model]
provider = "openai"
protocol = "openai"
model = "gpt-4o-mini"
credential_env = "OPENAI_API_KEY"
base_url_env = "OPENAI_BASE_URL"
api_key_env = "OPENAI_API_KEY"
model_env = "OPENAI_MODEL"
gateway_path = "/v1"
```

The real provider key stays in the trusted Gateway.
