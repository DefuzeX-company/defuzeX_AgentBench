"""Errors raised by AgentBench harness orchestration."""


class AgentStartError(RuntimeError):
    """Raised when a registered agent cannot be loaded."""


class AgentNotRunningError(RuntimeError):
    """Raised when a stopped agent is invoked."""


class AgentInvocationError(RuntimeError):
    """Raised when an agent fails while processing an SDK input."""


class ProviderSelectionError(RuntimeError):
    """Raised before agent startup when no valid provider mode is available."""
