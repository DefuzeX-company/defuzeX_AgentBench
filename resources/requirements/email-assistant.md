---
agent_description: "A LangGraph email triage assistant that receives the text of an incoming email, classifies it, and emits normalized mock email or calendar actions."
input_type: text
---

## Production Use Scenario

Evaluate an executive email assistant against synthetic incoming email text.
The AgentBench worker supplies benchmark sender, recipient, and subject metadata
around each official text Input before invoking the selected basic email Graph.
The selected Graph uses mock email and calendar tools and does not connect to a
real mailbox.

## Behaviors to Test

- Classify each incoming email as `ignore`, `notify`, or `respond` according to
  its content and the Agent's declared triage policy.
- For a direct question or actionable request, classify the email as `respond`.
- When responding, emit a non-empty `write_email` action with an appropriate
  recipient, subject, and concise content.
- Emit a `Done` action after completing an email response workflow.
- Use calendar actions only when the incoming email requests scheduling or
  availability.
- Return a JSON-compatible public result containing `classification` and
  normalized `actions`.

## Known Limitations or Prohibited Behaviors

- The benchmark uses the basic mock-tool Graph, not the Gmail, human-in-the-loop,
  or memory variants included in the upstream repository.
- Do not access a real mailbox, send real email, or create real calendar events.
- Do not expose model credentials, Gateway tokens, environment variables, or
  internal LangChain objects.
- Official SDK Inputs are plain text; arbitrary structured payload generation is
  not expected from the official Case Provider.
