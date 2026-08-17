"""Framework-specific agent adapters."""

from .base import AdapterInvocation, AgentAdapter, AgentDescriptor
from .factory import (
    DEFAULT_ADAPTER_FACTORY,
    AdapterFactory,
    AdapterFactoryError,
    UnsupportedAdapterError,
    create_adapter,
)

__all__ = [
    "AdapterFactory",
    "AdapterFactoryError",
    "AdapterInvocation",
    "AgentAdapter",
    "AgentDescriptor",
    "DEFAULT_ADAPTER_FACTORY",
    "UnsupportedAdapterError",
    "create_adapter",
]
