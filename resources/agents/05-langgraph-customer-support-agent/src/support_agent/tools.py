"""Customer support tools backed by deterministic benchmark mocks."""

from __future__ import annotations

from langchain_core.tools import tool

from benchmark_mocks import get_mock_service
from .prompts import INITIAL_GREETING


MOCK_ORDERS = get_mock_service().orders
MOCK_INVENTORY = get_mock_service().inventory


def _items_block(items: list[str]) -> str:
    return "\n".join(f"  - {item}" for item in items)


@tool
def search_knowledge_base(query: str, category: str = "general") -> str:
    """Search the store knowledge base for policies, products, and FAQ."""
    categories = [] if category == "general" else [category]
    results = get_mock_service().search_knowledge_base(
        query=query,
        max_results=3,
        min_similarity_score=0.0,
        categories=categories,
    )
    if not results:
        return "No relevant information found in the local benchmark knowledge base."

    blocks = [
        f"Category: {doc['category']}\n{doc['content']}"
        for doc, _score in results
    ]
    return "Knowledge Base Search Results\n\n" + "\n\n".join(blocks)


@tool
def search_vector_knowledge_base(
    query: str,
    max_results: int = 5,
    min_similarity_score: float = 0.0,
    categories: str = "",
) -> str:
    """Search the local benchmark knowledge base with deterministic scoring."""
    if isinstance(max_results, str):
        max_results = int(max_results) if max_results.isdigit() else 5
    if isinstance(min_similarity_score, str):
        try:
            min_similarity_score = float(min_similarity_score)
        except ValueError:
            min_similarity_score = 0.0

    category_list = [
        category.strip().lower()
        for category in categories.split(",")
        if category.strip()
    ]
    valid_categories = {"product", "shipping", "return", "payment", "general"}
    category_list = [category for category in category_list if category in valid_categories]

    results = get_mock_service().search_knowledge_base(
        query=query,
        max_results=max_results,
        min_similarity_score=max(0.0, min(1.0, min_similarity_score)),
        categories=category_list or None,
    )

    if not results:
        return "No relevant information found in the local benchmark knowledge base."

    formatted = [
        "Vector Knowledge Base Search Results",
        f"Query: {query!r}",
        "",
    ]
    for index, (doc, score) in enumerate(results, 1):
        formatted.extend(
            [
                f"Result #{index}",
                f"Similarity: {score:.3f}",
                f"Category: {doc['category']}",
                f"Type: {doc['type']}",
                doc["content"],
                "",
            ]
        )
    return "\n".join(formatted).strip()


@tool
def get_order_status(order_id: str) -> str:
    """Look up current status and tracking information for a customer order."""
    cleaned = order_id.replace("#", "").strip()
    order = get_mock_service().get_order_status(cleaned)
    if not order:
        return (
            f"Order #{cleaned} was not found in the benchmark order system. "
            "Please verify the order number."
        )

    if order["status"] == "in_transit":
        return f"""Order #{cleaned} - In Transit

Status: Your order is on its way.
Expected Delivery: {order['expected_delivery']}
Tracking Number: {order['tracking']}

Items:
{_items_block(order['items'])}"""

    if order["status"] == "delivered":
        return f"""Order #{cleaned} - Delivered

Status: Successfully delivered
Delivered: {order['delivered_date']}

Items:
{_items_block(order['items'])}"""

    if order["status"] == "processing":
        return f"""Order #{cleaned} - Processing

Status: Your order is being prepared for shipment.
Expected Ship Date: {order['expected_ship']}

Items:
{_items_block(order['items'])}"""

    return f"Order #{cleaned} status: {order['status']}"


@tool
def list_orders(status_filter: str = "all") -> str:
    """List orders and optionally filter them by status."""
    matches = get_mock_service().list_orders(status_filter=status_filter)
    if not matches:
        return f"No orders found for status filter {status_filter!r}."

    lines = [f"Orders matching {status_filter!r}: {len(matches)}"]
    for order_id, order in matches:
        lines.append(f"- #{order_id}: {order['status']} ({', '.join(order['items'])})")
    return "\n".join(lines)


@tool
def initiate_return(order_id: str, reason: str) -> str:
    """Start a return and produce deterministic return authorization details."""
    cleaned = order_id.replace("#", "").strip()
    result = get_mock_service().initiate_return(cleaned, reason)
    if result is None:
        return f"I couldn't find order #{cleaned}, so I cannot start a return."

    shipping_line = (
        "Free return shipping label will be emailed within 1 hour."
        if result["free_shipping"]
        else (
            "A return label email will be sent within 1 hour. "
            "$7.99 return shipping will be deducted from the refund."
        )
    )
    return f"""Return Authorized - Order #{cleaned}

Return Authorization: {result['return_id']}
Reason: {result['reason']}
Items: {', '.join(result['items'])}

{shipping_line}
Pack the item securely, attach the return label, and drop it off with UPS.
Refunds are processed within {result['refund_time']} after we receive the return."""


@tool
def check_product_availability(product_name: str) -> str:
    """Check whether a product is in stock in the benchmark inventory."""
    matches = get_mock_service().check_product_availability(product_name)
    if not matches:
        return f"I couldn't find inventory information for {product_name!r}."

    lines = ["Product Availability"]
    for product, details in matches:
        status_label = details["status"].replace("_", " ")
        line = f"- {product}: {status_label} ({details['stock']} units)"
        if details["status"] == "out_of_stock":
            line += f", restock expected {details.get('restock_date', 'TBD')}"
        lines.append(line)
    return "\n".join(lines)


@tool
def send_greeting() -> str:
    """Send a welcome greeting message to the customer."""
    return INITIAL_GREETING


@tool
def escalate_to_human(reason: str, customer_message: str) -> str:
    """Create a deterministic local support ticket for human escalation."""
    ticket = get_mock_service().escalate_to_human(reason, customer_message)
    if ticket["priority"] == "High":
        prefix = "I understand your frustration and I apologize for the inconvenience."
    else:
        prefix = "I've connected this issue with a human support specialist."

    return f"""{prefix}

Support Ticket: {ticket['ticket_id']}
Priority Level: {ticket['priority']}
Status: {ticket['status']}
Expected Response: {ticket['expected_response']}"""


FUNCTION_DESCRIPTIONS = {
    "search_vector_knowledge_base": "Search store policies, product information, and FAQ.",
    "get_order_status": "Look up order status, delivery dates, and tracking.",
    "list_orders": "List orders filtered by processing, in_transit, delivered, shipped, or all.",
    "initiate_return": "Start a return and generate an RMA.",
    "check_product_availability": "Check local benchmark inventory.",
    "escalate_to_human": "Create a local support ticket for human escalation.",
    "send_greeting": "Send a welcome message.",
}


@tool
def list_available_functions() -> str:
    """List all available customer support actions."""
    lines = ["Available Functions & Actions"]
    for name, description in FUNCTION_DESCRIPTIONS.items():
        lines.append(f"- {name}: {description}")
    return "\n".join(lines)


tools = [
    list_available_functions,
    send_greeting,
    search_vector_knowledge_base,
    get_order_status,
    list_orders,
    initiate_return,
    check_product_availability,
    escalate_to_human,
]
