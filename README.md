# DefuzeX AgentBench

## Overview

DefuzeX AgentBench is a benchmark for evaluating AI agents on end-to-end tasks
that require calling a target Agent, collecting its outputs and execution trace,
and judging whether it completed the requested workflow correctly.

Given a registered Agent and a benchmark Case, AgentBench runs the Agent through
a trusted host harness. The harness can launch framework-specific or
containerized Agents, route model traffic through a credential-safe Model
Gateway, record each SDK input and Agent response as append-only JSONL events,
and submit the completed run to the DefuzeX Judge.

AgentBench is designed to make Agent evaluation reproducible. Agents are
declared in a registry, adapted through framework adapters such as LangGraph,
certified from `adapting` to `ready`, and included in default benchmark runs only
after certification succeeds.

![DefuzeX AgentBench framework](figures/framework.png)

## Setup

DefuzeX AgentBench requires Python 3.10 or later and the DefuzeX Python SDK.
The SDK provides the benchmark protocol used by AgentBench: it parses benchmark
requirements, creates DefuzeX Cases, drives each SDK input, records evidence,
and submits completed runs for judging.

Create and activate a virtual environment from the benchmark workspace:

```powershell
cd C:\Song_startup\benchmark
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install AgentBench in editable mode:

```powershell
python -m pip install -e .\defuzeX_AgentBench
```

### Internal SDK Build

This repository currently depends on the internal DefuzeX SDK `dev` branch.
Until the SDK is published for normal package installation, if `Defuze-SDK` has
not been cloned locally yet, clone it from the SDK `dev` branch
(`https://github.com/DefuzeX-company/Defuze-SDK/tree/dev`) next to
`defuzeX_AgentBench`, then install it into the same `.venv`:

```powershell
cd C:\Song_startup\benchmark
git clone --branch dev --single-branch https://github.com/DefuzeX-company/Defuze-SDK.git
python -m pip install -e .\Defuze-SDK
python -m pip install -e .\defuzeX_AgentBench
```

The current local development environment is installed this way:
`defuzex` is linked from `C:\Song_startup\benchmark\Defuze-SDK`, and
`defuzex-agentbench` is linked from
`C:\Song_startup\benchmark\defuzeX_AgentBench`.

> [!NOTE]
> PAT means Personal Access Token. If the internal DefuzeX SDK repository is
> private, GitHub may require a PAT when cloning it over HTTPS. Treat the PAT
> like a password: keep it out of source files, README examples, notebooks, and
> committed `.env` files.

## Usage

After installing AgentBench, start it from the benchmark workspace with the
launcher script:

```powershell
cd C:\Song_startup\benchmark
.\.venv\Scripts\Activate.ps1
python .\run_agentbench.py
```

You can also run the package directly from the AgentBench repository:

```powershell
cd C:\Song_startup\benchmark\defuzeX_AgentBench
python -m agentbench
```

To save a run and inspect live benchmark events in the local result viewer, pass
an output path:

```powershell
python -m agentbench --output results\result.json
```

Without `--output`, AgentBench runs in the terminal and does not create a JSONL
result artifact. With `--output`, AgentBench writes an append-only JSONL result
file and starts the local viewer so you can refresh and inspect events while the
benchmark is running.

For more agent-facing instructions, start with [AGENTS.md](AGENTS.md). The
longer documentation guide is in [docs/AGENTS.md](docs/AGENTS.md).

## How to Add Agents to Testing

If you want to add your own Agent to the benchmark, ask an agent to read
[docs/How To Add Agent.md](docs/How%20To%20Add%20Agent.md) and follow the
onboarding flow documented there.

AgentBench provides the pieces needed to turn an external Agent project into a
repeatable benchmark target: registry-based discovery, framework adapters,
Docker runtime support, model credential routing through the Model Gateway,
append-only result artifacts, local result viewing, and certification from
`adapting` to `ready`. This gives you a consistent way to compare Agents across
the same DefuzeX Cases while keeping runtime behavior, outputs, and judgment
evidence inspectable.

## Citation and License

MIT License. See [LICENSE](LICENSE).

If you find our work helpful, please cite it as follows:
