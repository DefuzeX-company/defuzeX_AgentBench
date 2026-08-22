# LangGraph adapter

This adapter follows LangGraph's official application contract:

- `langgraph.json` owns graph discovery through `graphs.<graph_id>`.
- An entrypoint uses `file.py:attribute` and may expose a compiled graph,
  Functional API entrypoint, Pregel object, or zero-argument graph factory.
- AgentBehaviorBench (ABB) checks behavior through `invoke()` instead of depending on a
  concrete LangGraph implementation class.

The ABB-specific `agent.toml` selects the graph and maps benchmark values:

```toml
[adapter]
type = "langgraph"
mode = "in_process"
config = "langgraph.json"
graph_id = "agent"
input_key = "prompt"
output_key = "response"
```

Execution flow:

```text
registry -> agent.toml -> langgraph.json -> file.py:graph -> graph.invoke()
```

`LangGraphInvocation` preserves both the extracted benchmark output and the raw
graph state. The SDK-facing harness can submit `output` while retaining
`raw_output` as evidence.

`in_process` is intentionally the first execution mode. It is fast and useful
for compatible agents, but Python package names and dependency versions can
collide. A future isolated mode should keep the same adapter interface and move
loading/invocation into a per-agent subprocess or container.

Official references:

- https://docs.langchain.com/oss/python/langgraph/application-structure
- https://docs.langchain.com/oss/python/langgraph/use-functional-api
- https://github.com/langchain-ai/langgraph/blob/main/libs/cli/langgraph_cli/schemas.py
