"""Compatibility wrapper for local deterministic knowledge-base search.

The original project used HuggingFace embeddings. AgentBench forbids non-LLM
network access, so this module now delegates to `benchmark_mocks`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from benchmark_mocks import get_mock_service


@dataclass(frozen=True)
class Document:
    page_content: str
    metadata: dict[str, str]


class KnowledgeBaseVectorStore:
    """Small compatibility facade matching the original public methods."""

    def load_from_json(self, json_path: str) -> None:
        """Kept for compatibility; fixtures are loaded by benchmark_mocks."""
        return None

    def search(self, query: str, k: int = 3, filter_category: Optional[str] = None) -> str:
        categories = [filter_category] if filter_category else None
        results = get_mock_service().search_knowledge_base(
            query=query,
            max_results=k,
            categories=categories,
        )
        if not results:
            return "No relevant information found in the knowledge base."
        return "\n\n".join(doc["content"] for doc, _score in results)

    def search_with_scores(
        self,
        query: str,
        k: int = 5,
        filter_categories: Optional[list[str]] = None,
        score_threshold: float = 0.0,
    ) -> list[tuple[Document, float]]:
        results = get_mock_service().search_knowledge_base(
            query=query,
            max_results=k,
            min_similarity_score=score_threshold,
            categories=filter_categories,
        )
        return [
            (
                Document(
                    page_content=doc["content"],
                    metadata={"category": doc["category"], "type": doc["type"]},
                ),
                score,
            )
            for doc, score in results
        ]


_vector_store_instance: KnowledgeBaseVectorStore | None = None


def get_vector_store() -> KnowledgeBaseVectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = KnowledgeBaseVectorStore()
    return _vector_store_instance
