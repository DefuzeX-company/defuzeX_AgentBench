"""Declarative model provider configuration loaded from an agent manifest."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib  # type: ignore[no-redef]


class ModelConfigurationError(ValueError):
    """Raised when an agent's model declaration cannot be used safely."""


@dataclass(frozen=True, slots=True)
class ModelProviderConfig:
    """One concrete model endpoint selected for an agent run."""

    provider_id: str
    protocol: str
    model: str
    upstream_base_url: str
    credential_env: str

    @classmethod
    def from_agent_dir(
        cls,
        agent_root: str | Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> "ModelProviderConfig | None":
        root = Path(agent_root).resolve()
        with (root / "agent.toml").open("rb") as stream:
            manifest = tomllib.load(stream)
        model = manifest.get("model")
        if model is None:
            return None
        if not isinstance(model, dict):
            raise ModelConfigurationError("Manifest field [model] must be a table")

        values = os.environ if environ is None else environ
        override_env = _optional_string(model, "upstream_base_url_env")
        upstream = values.get(override_env, "") if override_env else ""
        upstream = upstream or _required_string(model, "upstream_base_url")
        _validate_http_url(upstream)

        return cls(
            provider_id=_required_string(model, "provider"),
            protocol=_required_string(model, "protocol").lower(),
            model=_required_string(model, "model"),
            upstream_base_url=upstream.rstrip("/"),
            credential_env=_required_string(model, "credential_env"),
        )


def _validate_http_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ModelConfigurationError(
            "Model upstream_base_url must be an absolute HTTP(S) URL"
        )
    if parsed.username or parsed.password or parsed.fragment:
        raise ModelConfigurationError(
            "Model upstream_base_url cannot contain credentials or a fragment"
        )


def _required_string(data: dict[str, object], key: str) -> str:
    value = _optional_string(data, key)
    if value is None:
        raise ModelConfigurationError(f"Model field must be non-empty: {key}")
    return value


def _optional_string(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ModelConfigurationError(f"Model field must be non-empty: {key}")
    return value.strip()
