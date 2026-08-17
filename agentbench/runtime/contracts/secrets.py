"""Secret resolution contracts for runtime implementations."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class MissingSecretError(RuntimeError):
    """Raised before startup when a declared secret is unavailable."""


@runtime_checkable
class SecretResolver(Protocol):
    def require(self, name: str) -> str:
        """Resolve a non-empty secret or stop startup."""


@dataclass(frozen=True, slots=True)
class EnvironmentSecretResolver:
    """Resolve explicitly named secrets from the process environment."""

    environ: Mapping[str, str] | None = None

    def require(self, name: str) -> str:
        values = os.environ if self.environ is None else self.environ
        value = values.get(name, "")
        if not value.strip():
            raise MissingSecretError(
                f"Required secret is not configured in the environment: {name}"
            )
        return value
