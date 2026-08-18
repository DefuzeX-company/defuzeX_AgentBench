FROM python:3.12-slim

WORKDIR /opt/model-gateway
COPY pyproject.toml ./
COPY src ./src
RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 gateway

USER gateway
ENTRYPOINT ["python", "-m", "defuzex_model_gateway.server"]
