# DefuzeX AgentBench

![Python](https://img.shields.io/badge/Python-3.10%2B-8a008a)
![License](https://img.shields.io/badge/License-MIT-0086c9)
![Package](https://img.shields.io/badge/pypi%20package-0.1.0-2acb16)

## News

- AgentBench now runs registered LangGraph agents through the DefuzeX SDK
  `get_input()` / `submit()` handshake.

## Overview

DefuzeX AgentBench is a lightweight benchmark harness for testing agent
behavior through the DefuzeX Python SDK. It keeps the benchmark runner,
framework adapters, agent fixtures, and runtime isolation code in one
installable package.

The current execution flow is:

```text
registry.toml
-> SuiteRunner
-> BenchmarkRunner
-> DefuzeX SDK Run
-> Agent Adapter / Runtime
-> Judge Report
```

The repository includes:

- `agentbench/cli`: terminal entry point and progress output.
- `agentbench/harness`: SDK handshake, suite execution, results, and registry.
- `agentbench/adapter`: framework-neutral adapter contract and LangGraph support.
- `agentbench/runtime`: local and Docker runtime integration.
- `resources/agents`: reproducible benchmark agent fixtures.
- `services/model-gateway`: trusted proxy for model provider access in Docker
  runs.

## Setup

Create and activate a Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install AgentBench from this repository:

```powershell
python -m pip install -e .
```

Set a DefuzeX API key when using official Case or Judge providers:

```powershell
$env:DEFUZEX_API_KEY = "dfx_<public-id>.<secret>"
```

Run the benchmark CLI:

```powershell
agentbench
```

Run the test suite:

```powershell
python -m pytest
```
