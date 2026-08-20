# Developer Setup

This AgentBench conversion intentionally does not use Ollama, LMStudio, LangSmith, or real customer support services.

## Required Runtime

- Python 3.11 or 3.12
- Docker for final acceptance
- One API key for the selected remote LLM provider

## Environment

Create `.env` from `.env.example`:

```text
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_key_here
MOCK_SCENARIO=default
LANGCHAIN_TRACING_V2=false
```

For OpenAI-compatible gateways, set `LLM_PROVIDER=openai-compatible`, `LLM_BASE_URL`, and `LLM_API_KEY`.

## Mock Services

All non-LLM business capabilities live in `benchmark_mocks/`:

- orders
- returns
- inventory
- knowledge base search
- helpdesk escalation

The mock service records every operation so the smoke script can verify no real business service was used.

## Smoke Test

```bash
python scripts/smoke.py
```

The script prints:

- final customer-facing response
- mock operation trace
- non-zero exit code if required support operations are missing
