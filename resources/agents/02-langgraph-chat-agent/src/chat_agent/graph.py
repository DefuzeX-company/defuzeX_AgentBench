"""Stateful one-node LangGraph chatbot."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

SYSTEM_MESSAGE = SystemMessage(
    content="You are a helpful conversational assistant. Answer clearly and concisely."
)


class ChatState(MessagesState):
    prompt: str
    response: str


_model: BaseChatModel | None = None


def _get_model() -> BaseChatModel:
    global _model
    if _model is not None:
        return _model
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Set it in the environment before "
            "running this agent."
        )

    from langchain_openai import ChatOpenAI

    _model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        temperature=0,
    )
    return _model


def chat(state: ChatState) -> dict[str, object]:
    """Append the user prompt and one model response to conversation state."""

    user_message = HumanMessage(content=state["prompt"].strip())
    reply = _get_model().invoke(
        [SYSTEM_MESSAGE, *state.get("messages", []), user_message]
    )
    if not isinstance(reply, AIMessage):
        reply = AIMessage(content=str(reply.content))
    response = reply.content if isinstance(reply.content, str) else str(reply.content)
    return {"messages": [user_message, reply], "response": response}


graph = (
    StateGraph(ChatState)
    .add_node("chat", chat)
    .add_edge(START, "chat")
    .add_edge("chat", END)
    .compile(checkpointer=InMemorySaver())
)
