# Minimal LangGraph Chat Agent

A small stateful chatbot built with LangGraph's Graph API. It stores message
history in memory and uses an OpenAI chat model to generate responses.

## Setup

```powershell
cd resources\agents\02-langgraph-chat-agent
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

Set `OPENAI_API_KEY` in the environment. Optionally set `OPENAI_MODEL`; its
default value is `gpt-4.1-mini`.

## Run

```powershell
python -m chat_agent.cli
```

Enter messages at the `You>` prompt. Enter `exit` or `quit` to stop.

## Input And Output

The graph accepts `{"prompt": "Hello"}` and returns state containing a
`response` string and accumulated `messages`. Calls using the same LangGraph
`thread_id` share conversation history.
