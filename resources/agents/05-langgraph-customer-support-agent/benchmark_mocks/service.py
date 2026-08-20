"""Local deterministic mock services for the customer support agent."""

from __future__ import annotations

import hashlib
import json
import os
import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


FIXTURE_DIR = Path(__file__).parent / "fixtures"


@dataclass(frozen=True)
class MockOperation:
    service: str
    operation: str
    summary: str


class CustomerSupportMockService:
    """Business-specific local substitute for support databases and services."""

    def __init__(self, scenario: str = "default") -> None:
        self.scenario = scenario
        fixture_path = FIXTURE_DIR / f"{scenario}.json"
        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Mock scenario {scenario!r} not found at {fixture_path}. "
                "No real service fallback is allowed."
            )

        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.orders: dict[str, dict[str, Any]] = deepcopy(data["orders"])
        self.inventory: dict[str, dict[str, Any]] = deepcopy(data["inventory"])
        self.knowledge_base: list[dict[str, str]] = deepcopy(data["knowledge_base"])
        self._trace: list[MockOperation] = []

    def reset_trace(self) -> None:
        self._trace.clear()

    def get_trace(self) -> list[MockOperation]:
        return list(self._trace)

    def get_trace_as_dicts(self) -> list[dict[str, str]]:
        return [asdict(entry) for entry in self._trace]

    def _record(self, service: str, operation: str, summary: str) -> None:
        self._trace.append(MockOperation(service, operation, summary))

    @staticmethod
    def _clean_order_id(order_id: str) -> str:
        return order_id.replace("#", "").strip()

    @staticmethod
    def _stable_code(prefix: str, *parts: str, digits: int = 4) -> str:
        digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
        value = int(digest[:12], 16) % (10 ** digits)
        return f"{prefix}-{value:0{digits}d}"

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", text.lower())
            if len(token) > 2
        }

    def search_knowledge_base(
        self,
        query: str,
        max_results: int = 5,
        min_similarity_score: float = 0.0,
        categories: list[str] | None = None,
    ) -> list[tuple[dict[str, str], float]]:
        query_tokens = self._tokens(query)
        categories_set = set(categories or [])
        scored: list[tuple[dict[str, str], float]] = []

        for doc in self.knowledge_base:
            if categories_set and doc["category"] not in categories_set:
                continue
            doc_tokens = self._tokens(" ".join(doc.values()))
            overlap = len(query_tokens & doc_tokens)
            score = overlap / max(len(query_tokens), 1)
            if score >= min_similarity_score:
                scored.append((doc, score))

        scored.sort(key=lambda item: (item[1], item[0]["category"]), reverse=True)
        results = scored[: max(1, min(10, int(max_results)))]
        self._record(
            "knowledge_base",
            "search",
            f"query={query!r}, categories={categories or 'all'}, results={len(results)}",
        )
        return results

    def get_order_status(self, order_id: str) -> dict[str, Any] | None:
        cleaned = self._clean_order_id(order_id)
        order = self.orders.get(cleaned)
        self._record(
            "orders",
            "get_order_status",
            f"order_id={cleaned}, found={order is not None}",
        )
        return deepcopy(order) if order else None

    def list_orders(self, status_filter: str = "all") -> list[tuple[str, dict[str, Any]]]:
        status_filter_lower = status_filter.lower().strip()
        status_mapping = {
            "not_shipped": ["processing"],
            "pending": ["processing"],
            "unshipped": ["processing"],
            "shipped": ["in_transit", "delivered"],
            "all": None,
        }
        target_statuses = status_mapping.get(status_filter_lower, [status_filter_lower])

        matches = [
            (order_id, deepcopy(order))
            for order_id, order in self.orders.items()
            if target_statuses is None or order["status"] in target_statuses
        ]
        self._record(
            "orders",
            "list_orders",
            f"status_filter={status_filter_lower}, results={len(matches)}",
        )
        return matches

    def initiate_return(self, order_id: str, reason: str) -> dict[str, Any] | None:
        cleaned = self._clean_order_id(order_id)
        order = self.orders.get(cleaned)
        self._record(
            "returns",
            "initiate_return",
            f"order_id={cleaned}, reason={reason}, found={order is not None}",
        )
        if not order:
            return None

        normalized_reason = reason.lower()
        free_shipping = any(
            marker in normalized_reason
            for marker in ("defect", "damaged", "broken", "wrong_item")
        )
        return {
            "order_id": cleaned,
            "return_id": self._stable_code("RMA", cleaned, reason, digits=6),
            "reason": reason,
            "items": deepcopy(order["items"]),
            "free_shipping": free_shipping,
            "refund_time": "5-7 business days",
        }

    def check_product_availability(
        self, product_name: str
    ) -> list[tuple[str, dict[str, Any]]]:
        product_lower = product_name.lower().strip()
        matches = [
            (name, deepcopy(details))
            for name, details in self.inventory.items()
            if name in product_lower or product_lower in name
        ]
        self._record(
            "inventory",
            "check_product_availability",
            f"product={product_name!r}, results={len(matches)}",
        )
        return matches

    def escalate_to_human(self, reason: str, customer_message: str) -> dict[str, str]:
        priority = "High" if re.search(r"frustrated|angry|upset", reason, re.I) else "Standard"
        ticket_id = self._stable_code("TICKET", reason, customer_message, digits=4)
        expected_response = "Within 15 minutes" if priority == "High" else "Within 30 minutes"
        self._record(
            "helpdesk",
            "escalate_to_human",
            f"ticket_id={ticket_id}, priority={priority}, reason={reason}",
        )
        return {
            "ticket_id": ticket_id,
            "priority": priority,
            "status": "Assigned to Senior Support Team" if priority == "High" else "Assigned to agent",
            "expected_response": expected_response,
        }


_service: CustomerSupportMockService | None = None


def get_mock_service() -> CustomerSupportMockService:
    global _service
    scenario = os.getenv("MOCK_SCENARIO", "default")
    if _service is None or _service.scenario != scenario:
        _service = CustomerSupportMockService(scenario=scenario)
    return _service


def reset_mock_service() -> CustomerSupportMockService:
    global _service
    _service = CustomerSupportMockService(scenario=os.getenv("MOCK_SCENARIO", "default"))
    return _service
