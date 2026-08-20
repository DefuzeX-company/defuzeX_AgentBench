FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    LLM_PROVIDER=openai \
    OPENAI_MODEL=gpt-4o-mini \
    SWE_AGENT_CONFIG_ROOT=/opt/agent \
    SWE_AGENT_CONFIG_DIR=/opt/agent/config \
    SWE_AGENT_TOOLS_DIR=/opt/agent/tools \
    SWE_AGENT_TRAJECTORY_DIR=/tmp/agentbench-home/trajectories \
    AGENTBENCH_WORKSPACE_ROOT=/tmp/agentbench-workspaces \
    SWE_AGENT_RUNTIME_HOME=/tmp/agentbench-home \
    SWE_AGENT_TOOLS_ROOT=/run/agentbench-tools \
    SWE_AGENT_ENV_FILE=/tmp/agentbench-home/.swe-agent-env \
    SWE_AGENT_MODEL_PATCH=/tmp/agentbench-home/model.patch

WORKDIR /opt/agent

RUN apt-get update \
    && apt-get install -y --no-install-recommends git bash ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY config ./config
COPY tools ./tools

RUN python -m pip install --no-cache-dir . \
    && find /opt/agent/tools -type f -path '*/bin/*' -exec sed -i 's/\r$//' {} + \
    && find /opt/agent/tools -type f -path '*/bin/*' -exec chmod +x {} + \
    && useradd --create-home --uid 10001 agent \
    && mkdir -p /tmp/agentbench-workspaces /tmp/agentbench-home /tmp/agentbench-home/trajectories /run/agentbench-tools \
    && chown -R agent:agent /tmp/agentbench-workspaces /tmp/agentbench-home /run/agentbench-tools

USER agent
