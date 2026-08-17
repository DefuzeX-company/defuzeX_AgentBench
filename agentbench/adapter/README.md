# Adapter layer

The adapter layer translates framework-specific execution into one contract:

```text
Harness -> create_adapter(agent) -> AgentAdapter -> AdapterInvocation
```

Responsibilities:

- `base.py` defines framework-neutral input/output contracts.
- `factory.py` maps a framework name to an adapter builder.
- Framework packages such as `langgraph/` own loading and invocation details.
- The harness depends only on `AgentAdapter`, never on a concrete framework.

To add a framework, implement `AgentAdapter` and register its builder:

```python
DEFAULT_ADAPTER_FACTORY.register("crewai", CrewAIAdapter.from_agent_dir)
```

Registration is explicit. Import scanning and naming conventions are not used,
so supported frameworks remain visible, deterministic, and easy to test :)
