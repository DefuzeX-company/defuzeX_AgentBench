# DefuzeX AgentBench

Run the benchmark interactively:

```powershell
python -m agentbench
# Equivalent explicit form:
python -m agentbench run
```

Default runs include only registrations with both `enabled = true` and
`status = "ready"`.

To preserve cases, outputs, and trace-like adapter state, provide an output path:

```powershell
python -m agentbench --output results\result.json
```

Each run creates a uniquely named append-only JSONL artifact, such as
`results\result-20260819-025720.jsonl`. The local result viewer starts without
requiring Node.js and remains available after the benchmark finishes:

- Press `r` to stop the viewer and run the benchmark again.
- Press `q` to stop the viewer and exit.
- Use the viewer's Refresh button to load events written during a run.

Open a saved result later with:

```powershell
python -m agentbench view results\result-20260819-025720.jsonl
```

After adapting a new Agent, certify only that registration:

```powershell
python -m agentbench certify swe-agent
```

Certification runs the full DefuzeX benchmark flow, writes a unique append-only
artifact under `results/` by default, and changes the Agent from `adapting` to
`ready` only when the complete suite passes. A failure leaves the Registry
unchanged.
