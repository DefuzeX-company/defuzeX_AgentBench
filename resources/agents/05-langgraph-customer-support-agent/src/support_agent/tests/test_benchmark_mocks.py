"""Tests for AgentBench mock service behavior."""

from benchmark_mocks import reset_mock_service


def test_mock_trace_records_expected_operations():
    service = reset_mock_service()

    service.get_order_status("123456")
    service.search_knowledge_base("return policy for defective order", categories=["return"])
    service.initiate_return("123456", "defective")
    service.escalate_to_human("customer_frustrated", "This arrived defective")

    observed = {
        (entry.service, entry.operation)
        for entry in service.get_trace()
    }

    assert ("orders", "get_order_status") in observed
    assert ("knowledge_base", "search") in observed
    assert ("returns", "initiate_return") in observed
    assert ("helpdesk", "escalate_to_human") in observed


def test_mock_return_ids_are_deterministic():
    service = reset_mock_service()

    first = service.initiate_return("123456", "defective")
    second = service.initiate_return("123456", "defective")

    assert first is not None
    assert second is not None
    assert first["return_id"] == second["return_id"]
