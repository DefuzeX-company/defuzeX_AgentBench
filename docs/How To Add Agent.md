# How to Add an Agent

This is the short path for adding a LangGraph Agent to DefuzeX AgentBench.
Detailed background lives in the linked Agent docs.

## Happy Path

Start with a LangGraph Agent that already runs locally:

```powershell
python -m agentbench certify <agent-id>
python -m agentbench run
```

The ideal onboarding experience is that everything before `certify` can be
generated or copied from templates. Until that CLI scaffolder exists, use this
checklist:

1. Put the source Agent through the AgentFactory conversion flow.
2. Copy the converted Agent into `resources/agents/<order>-<agent-id>/`.
3. Add `resources/agents/<order>-<agent-id>/agent.toml`.
4. Add `resources/requirements/<agent-id>.md`.
5. Add an entry in `resources/registry.toml` with `enabled = true` and
   `status = "adapting"`.
6. Run the focused tests for registry, Docker config, model binding, and the
   worker.
7. Run `python -m agentbench certify <agent-id>`.

`certify` promotes the Agent to `ready` when every requested Case completes
without invocation or runtime errors. A Judge failure means the Agent ran but
performed poorly on the benchmark; it does not mean the adapter is broken.

## What To Read

Read only the page you need:

- [AgentFactory Flow](./Agents/Factory.md): convert a downloaded Agent into a
  deterministic, Docker-runnable AgentBench candidate.
- [Runtime Contract](./Agents/Runtime.md): Docker, package data, JSONL worker,
  model Gateway, and filesystem rules.
- [Certification](./Agents/Certify.md): `adapting` to `ready`, result artifacts,
  and Judge failure semantics.
- [Troubleshooting](./Agents/Troubleshooting.md): search by observed error.
- [Full Reference](./Agents/Reference.md): the original complete reference.

## Definition of Done

An Agent is onboarded when:

- Docker starts it as non-root under AgentBench runtime policy.
- The JSONL worker accepts SDK Inputs and returns serializable `output` and
  `raw_output`.
- Model traffic goes through the trusted Gateway.
- Static fixtures and config files exist in the installed image.
- Runtime writes go to allowed paths.
- `python -m agentbench certify <agent-id>` exits `0` and writes JSONL evidence.
- The Registry status for that Agent is `ready`.
