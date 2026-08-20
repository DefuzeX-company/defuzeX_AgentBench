---
agent_description: "A LangGraph customer support agent for an electronics store that answers customer questions, checks mock order data, explains policies, starts returns, and escalates frustrated customers through deterministic local support tools."
input_type: text
---

## Production Use Scenario

Evaluate a customer support assistant that receives natural-language customer
messages for an online electronics store. The selected Graph uses local
deterministic mocks for order lookup, return authorization, inventory checks,
knowledge-base search, and human escalation. The Agent must use its tools to
ground responses in observable support actions instead of inventing order or
policy details.

## Behaviors to Test

- Answer customer support questions with a clear, customer-facing final response.
- Check order status when the customer provides an order number or asks about an order.
- Search the local knowledge base before explaining return, shipping, warranty, or policy details.
- Start a return and provide return authorization details when the customer requests a return for an eligible order.
- Escalate to a human support ticket when the customer is frustrated, angry, or asks for a human.
- Return JSON-compatible public output containing the final response, normalized tool actions, and mock operation trace.

## Known Limitations or Prohibited Behaviors

- The benchmark uses deterministic local mock services only; do not contact real order, CRM, inventory, shipping, vector database, or helpdesk systems.
- Do not expose model credentials, Gateway tokens, environment variables, request headers, or internal LangChain objects.
- Official SDK Inputs are plain text; arbitrary structured payload generation is not expected from the official Case Provider.
- The Agent may describe display-only tracking URLs from mock data, but it must not perform public web requests.
