"""
Retrieval module.

Wraps the Chroma vector store as a LangChain retriever, with a similarity
score threshold to help filter out weak matches before they reach the LLM
(one of the simplest, cheapest hallucination-reduction levers).
"""
from __future__ import annotations

from langchain_core.documents import Document

from src.config import settings
from src.ingestion.indexer import get_vectorstore


def get_retriever(k: int | None = None):
    vectorstore = get_vectorstore()
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k or settings.top_k},
    )


def retrieve_with_scores(query: str, k: int | None = None) -> list[tuple[Document, float]]:
    """Retrieve chunks along with their similarity scores (useful for
    debugging and for the "no relevant context found" guardrail)."""
    vectorstore = get_vectorstore()
    return vectorstore.similarity_search_with_relevance_scores(query, k=k or settings.top_k)
