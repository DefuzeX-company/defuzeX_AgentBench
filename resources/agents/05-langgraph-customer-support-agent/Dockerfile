FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LANGCHAIN_TRACING_V2=false \
    MOCK_SCENARIO=default \
    LLM_PROVIDER=openai

WORKDIR /opt/agent
COPY pyproject.toml README.md ./
COPY benchmark_mocks ./benchmark_mocks
COPY src ./src
COPY langgraph.json ./

RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 agent

USER agent
