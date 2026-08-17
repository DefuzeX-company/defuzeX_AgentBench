FROM python:3.12-slim

WORKDIR /opt/agentbench
COPY pyproject.toml ./
COPY agentbench ./agentbench
RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 gateway

USER gateway
ENTRYPOINT ["python", "-m", "agentbench.model.gateway"]
