"""Framework-neutral adapter for agents executed in containers."""

from .adapter import ContainerAgentAdapter
from .config import AgentContainerConfig, ContainerConfigurationError, runtime_type

__all__ = [
    "AgentContainerConfig",
    "ContainerAgentAdapter",
    "ContainerConfigurationError",
    "runtime_type",
]
