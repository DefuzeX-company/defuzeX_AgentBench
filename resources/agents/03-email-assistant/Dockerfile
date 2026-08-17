FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/agent
COPY pyproject.toml ./
COPY src ./src

# Install only the dependencies needed by the selected benchmark graph. The
# upstream project also declares notebook, evaluation, and Gmail tooling.
RUN python -m pip install --no-cache-dir \
        "html2text>=2024.2.26" \
        "langchain>=1,<2" \
        "langchain-openai>=1,<2" \
        "langgraph>=1,<2" \
        "python-dotenv>=1,<2" \
    && python -m pip install --no-cache-dir --no-deps . \
    && useradd --create-home --uid 10001 agent

USER agent
