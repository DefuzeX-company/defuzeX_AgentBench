"""Bind an agent's model-facing environment to one selected provider."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib  # type: ignore[no-redef]

from .provider import ModelConfigurationError, ModelProviderConfig


class SecretResolver(Protocol):
    def require(self, name: str) -> str:
        ...


@dataclass(frozen=True, slots=True)
class ModelInterface:
    """Environment variable names understood by one agent implementation."""

    protocol: str
    base_url_env: str
    api_key_env: str
    model_env: str
    gateway_path: str = ""


@dataclass(frozen=True, slots=True)
class ModelBinding:
    """Resolved provider, upstream credential, and agent interface."""

    provider: ModelProviderConfig
    interface: ModelInterface
    upstream_api_key: str

    @classmethod
    def from_agent_dir(
        cls,
        agent_root: str | Path,
        *,
        secret_resolver: SecretResolver,
        environ: Mapping[str, str] | None = None,
        provider: ModelProviderConfig | None = None,
    ) -> "ModelBinding | None":
        root = Path(agent_root).resolve()
        selected = provider or ModelProviderConfig.from_agent_dir(
            root, environ=environ
        )
        if selected is None:
            return None

        with (root / "agent.toml").open("rb") as stream:
            manifest = tomllib.load(stream)
        model = manifest.get("model")
        if not isinstance(model, dict):  # pragma: no cover - provider checked it
            raise ModelConfigurationError("Manifest field [model] must be a table")

        interface = ModelInterface(
            protocol=_required_string(model, "protocol").lower(),
            base_url_env=_required_string(model, "base_url_env"),
            api_key_env=_required_string(model, "api_key_env"),
            model_env=_required_string(model, "model_env"),
            gateway_path=_gateway_path(model.get("gateway_path", "")),
        )
        if interface.protocol != selected.protocol:
            raise ModelConfigurationError(
                f"Agent protocol {interface.protocol!r} is incompatible with "
                f"provider protocol {selected.protocol!r}"
            )

        return cls(
            provider=selected,
            interface=interface,
            upstream_api_key=secret_resolver.require(selected.credential_env),
        )

    def agent_environment(self, gateway_url: str, gateway_token: str) -> dict[str, str]:
        return {
            self.interface.base_url_env: (
                gateway_url.rstrip("/") + self.interface.gateway_path
            ),
            self.interface.api_key_env: gateway_token,
            self.interface.model_env: self.provider.model,
        }


def _required_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ModelConfigurationError(f"Model field must be non-empty: {key}")
    return value.strip()


def _gateway_path(value: object) -> str:
    if not isinstance(value, str):
        raise ModelConfigurationError("Model gateway_path must be a string")
    value = value.strip()
    if value and not value.startswith("/"):
        raise ModelConfigurationError("Model gateway_path must start with '/'")
    return value.rstrip("/")
