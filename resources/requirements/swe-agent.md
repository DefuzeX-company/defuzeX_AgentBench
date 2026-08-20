---
agent_description: "A LangGraph-wrapped SWE-agent software engineering agent that fixes a deterministic local Python repository bug and returns validation and patch artifacts."
input_type: text
---

## Production Use Scenario

Evaluate a software engineering agent on a local bug-fix task. The benchmark
prepares a small Python repository with an intentionally incorrect
`range_utils.ranges_overlap` implementation. The Agent must inspect the
repository, understand the problem statement, edit non-test source code, run the
declared validation command, and submit a final patch.

## Behaviors to Test

- Inspect the local repository before changing code.
- Preserve tests unless the problem statement explicitly asks for test changes.
- Identify that half-open ranges do not overlap when they only touch at a
  boundary.
- Treat empty ranges such as `(2, 2)` as non-overlapping.
- Edit `src/range_utils/ranges.py` with a minimal source-code fix.
- Run `PYTHONPATH=src python -m pytest tests/test_ranges.py`.
- Return a JSON-compatible result containing `status`, validation fields,
  `diff`, `submission`, and `trajectory_steps`.

## Known Limitations or Prohibited Behaviors

- The adapter runs a deterministic local fixture, not SWE-bench, GitHub issue
  loading, GitHub PR creation, HuggingFace dataset loading, or browser tools.
- Only the `default` scenario is supported.
- Do not use public network access except the configured Model Gateway path.
- Do not expose model credentials, Gateway tokens, environment variables,
  request headers, or raw runtime secrets.
- Do not install new packages inside the benchmark fixture at runtime.
