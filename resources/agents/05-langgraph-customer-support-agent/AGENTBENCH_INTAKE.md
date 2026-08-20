# AgentBench Intake: langgraph-customer-support-agent

## Source

- Repository: https://github.com/aperritano/langgraph-customer-support-agent.git
- Commit before conversion: `64dea78`
- License: MIT, declared in `pyproject.toml` and README
- Queue: `DoneAgents/langgraph-customer-support-agent`

## Expected Task

Customer says:

```text
I'm really frustrated. Order #123456 arrived defective. Check my order, explain the return policy, start a return, and escalate if needed.
```

Expected successful behavior:

- Use order data to identify order `123456` and its items/tracking status.
- Use the local knowledge base to explain the 30-day return policy and defective-item free return shipping.
- Initiate a return with an RMA for a defective item.
- Escalate the frustrated customer to a human support ticket.
- Emit a final customer-facing answer that summarizes the order status, return policy, RMA/return next steps, and escalation ticket.

## Stage 1 Analysis

Graph entry:

- `langgraph.json` declares `agent: src.support_agent.agent:graph`.
- `src/support_agent/agent.py` builds a `StateGraph(SupportState)` with:
  - node `agent`: calls the chat model with `SYSTEM_PROMPT` and conversation messages.
  - node `tools`: `ToolNode(tools)`.
  - conditional edge `agent -> tools` when the last `AIMessage` has tool calls.
  - edge `tools -> agent`, forming a ReAct loop.

State:

- `src/support_agent/state.py` defines `SupportState`.
- State contains only `messages: Annotated[list[BaseMessage], add_messages]`.

Original model dependency:

- `src/support_agent/agent.py` imports `langchain_ollama.ChatOllama`.
- The model is created at import time with `model="llama3.1:latest"` and `OLLAMA_BASE_URL`.
- This violates AgentFactory requirements because it needs a local Ollama runtime.

Original business tools:

- `list_available_functions`
- `send_greeting`
- `search_vector_knowledge_base`
- `get_order_status`
- `list_orders`
- `initiate_return`
- `check_product_availability`
- `escalate_to_human`

External/network risk inventory:

- LLM: Ollama HTTP endpoint at `OLLAMA_BASE_URL`. Must be replaced with API-key remote provider.
- Embeddings: `langchain_huggingface.HuggingFaceEmbeddings` with `sentence-transformers/all-MiniLM-L6-v2`; may download model files. Must be replaced or made fully local/deterministic for benchmark mode.
- LangSmith evaluation scripts call hosted LangSmith APIs. Keep as optional documentation only; do not use in benchmark smoke/e2e.
- API client scripts call a local LangGraph server only. They are not external business services.
- Business tools currently use in-memory mock data and local JSON; move them behind `benchmark_mocks/`.
- Tool output includes `https://track.example.com/...` as display text only; do not perform HTTP calls.

Mock plan:

- Create a standalone `benchmark_mocks/` package.
- Move fixtures into `benchmark_mocks/fixtures/`:
  - orders
  - inventory
  - knowledge base
- Implement a `CustomerSupportMockService` with deterministic operations:
  - `search_knowledge_base`
  - `get_order_status`
  - `list_orders`
  - `initiate_return`
  - `check_product_availability`
  - `escalate_to_human`
  - `get_trace`
  - `reset_trace`
- Replace HuggingFace vector search with deterministic local text scoring in the mock service.
- Ensure no failed mock operation falls back to real network services.

Runtime plan:

- Replace direct `ChatOllama` construction with a model factory.
- Default provider: OpenAI-compatible, configured with `LLM_PROVIDER=openai`.
- Required env: `OPENAI_API_KEY` for OpenAI-compatible provider.
- Optional env: `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TEMPERATURE`.
- Provide `.env.example` without secrets.
- Update Dockerfile to run without Ollama/LMStudio and avoid host service dependencies.
- Add a non-interactive smoke/e2e script for the expected task and mock trace validation.
