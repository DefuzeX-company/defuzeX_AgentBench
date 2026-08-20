# LangGraph Customer Support Agent for AgentBench

This is a converted LangGraph customer support agent. It keeps the original ReAct workflow and support tools, but removes local model runtimes and real business-service network calls.

## What It Does

- Answers customer support questions for an online electronics store.
- Uses LangGraph with an `agent -> tools -> agent` ReAct loop.
- Calls tools for order status, return policy search, return initiation, inventory lookup, and human escalation.
- Uses deterministic local business mocks from `benchmark_mocks/`.
- Uses one API-key configured remote LLM provider.

## Configuration

Copy `.env.example` to `.env` and set an API key:

```text
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_key_here
MOCK_SCENARIO=default
LANGCHAIN_TRACING_V2=false
```

OpenAI-compatible gateways may use:

```text
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://your-compatible-endpoint/v1
LLM_API_KEY=your_key_here
```

No Ollama, LMStudio, LangSmith, hosted search, hosted vector DB, CRM, order API, or inventory API is required.

## Graph

`langgraph.json` exports:

```text
agent = ./src/support_agent/agent.py:graph
```

AgentBench launches the persistent JSONL worker:

```text
python -m support_agent.worker
```

Input is an SDK text payload or a JSON object with `messages`, `message`,
`prompt`, or `customer_message`. The worker maps it to the LangGraph state:

```json
{"messages": [{"role": "user", "content": "Check order #123456"}]}
```

For each input line, stdout emits exactly one JSON response:

```json
{"ok": true, "output": {"final_response": "...", "actions": [], "mock_operations": []}, "raw_output": {}}
```

Graph and dependency diagnostics are redirected to stderr.

## Expected AgentBench Task

```text
I'm really frustrated. Order #123456 arrived defective. Check my order, explain the return policy, start a return, and escalate if needed.
```

Expected mock operations:

- `orders.get_order_status`
- `knowledge_base.search`
- `returns.initiate_return`
- `helpdesk.escalate_to_human`

## Local Commands

Install dependencies:

```bash
pip install -r requirements.txt
pip install "langgraph-cli[inmem]"
```

Run unit tests:

```bash
python -m pytest src/support_agent/tests -m "not integration"
```

Run the non-interactive smoke/e2e task:

```bash
python scripts/smoke.py
```

Run LangGraph server:

```bash
langgraph dev --host 0.0.0.0 --port 2024
```

## Docker

Build:

```bash
docker build -t agentbench-langgraph-customer-support:local .
```

Run the JSONL worker failure-path check without a model key:

```bash
echo '{"input":"hi"}' | docker run --rm -i -e LLM_PROVIDER=openai agentbench-langgraph-customer-support:local python -m support_agent.worker
```

AgentBench does not pass the real provider key into this container. The trusted
Model Gateway injects:

```text
LLM_BASE_URL=<gateway-url>/v1
LLM_API_KEY=<temporary-run-token>
LLM_MODEL=gpt-4.1-mini
```

The image runs as UID `10001`.
