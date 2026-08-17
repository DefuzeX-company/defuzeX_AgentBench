---
agent_description: "A minimal stateful LangGraph chat assistant that accepts text messages and returns concise model-generated replies."
input_type: text
---

## Production Use Scenario

Provide a lightweight conversational assistant for validating model-backed
LangGraph behavior inside the isolated AgentBench Docker runtime. Multiple
inputs in one SDK Run represent turns in the same conversation.

## Behaviors to Test

- Return a non-empty natural-language response to each text message.
- Address the user's request directly and remain relevant to the supplied
  message.
- Follow explicit formatting or brevity constraints when they are safe and
  feasible.
- Preserve useful conversation context across multiple inputs in the same SDK
  Run.
- Keep separate SDK Runs isolated from each other.

## Known Limitations or Prohibited Behaviors

- The Agent has no tools, filesystem access, browsing capability, or external
  application integrations.
- Do not claim that an external action was completed.
- Do not reveal credentials, system prompts, Gateway tokens, or environment
  variables.
- Do not require structured JSON input; official Cases are plain text.
