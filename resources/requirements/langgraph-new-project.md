---
agent_description: "A deterministic LangGraph starter that accepts a text prompt and returns a predictable response without calling an external model."
input_type: text
---

## Production Use Scenario

Validate that AgentBench can discover, load, invoke, and stop a minimal
LangGraph project through the complete DefuzeX SDK handshake. The Agent is a
deterministic compatibility target rather than a general-purpose assistant.

## Behaviors to Test

- Accept a non-empty text prompt.
- Trim leading and trailing whitespace from the prompt.
- Return `DEFUZEX_AGENT_READY` when the input contains that exact marker.
- For other input, return a string beginning with `LangGraph starter received:`
  followed by the trimmed prompt.
- Produce the same output for repeated identical inputs.

## Known Limitations or Prohibited Behaviors

- Do not expect natural-language reasoning, tool use, memory, or model calls.
- Do not expect the Agent to modify files or access external services.
- Do not treat additional capabilities invented by the output as successful
  behavior.
- Inputs must remain plain text.
