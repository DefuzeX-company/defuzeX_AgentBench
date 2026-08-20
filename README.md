# DefuzeX AgentBench

Run the benchmark interactively:

```powershell
python -m agentbench
```

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
