ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}
WORKDIR /opt/agent
COPY . .
RUN python -m pip install --no-cache-dir .
ENTRYPOINT ["python", "-m", "agent.cli"]
