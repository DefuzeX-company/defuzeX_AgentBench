"""Deterministic customer-support mocks for AgentBench."""

from .service import (
    CustomerSupportMockService,
    MockOperation,
    get_mock_service,
    reset_mock_service,
)

__all__ = [
    "CustomerSupportMockService",
    "MockOperation",
    "get_mock_service",
    "reset_mock_service",
]
