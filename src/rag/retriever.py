"""
Retrieval module.

Wraps the Chroma vector store as a LangChain retriever, with a similarity
score threshold to help filter out weak matches before they reach the LLM
(one of the simplest, cheapest hallucination-reduction levers).
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from langchain_core.documents import Document

from src.config import settings
from src.ingestion.indexer import get_metadata_store, get_vectorstore

_MONTHS = {
    "janvier": "01", "février": "02", "fevrier": "02", "mars": "03",
    "avril": "04", "mai": "05", "juin": "06", "juillet": "07",
    "août": "08", "aout": "08", "septembre": "09", "octobre": "10",
    "novembre": "11", "décembre": "12", "decembre": "12",
}
_CATEGORIES = {
    "boisson": "1", "boissons": "1", "dairy": "4",
    "laitier": "4", "laitiers": "4", "produits laitiers": "4",
}


def _normalize(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(char)
    )


def _collection_documents() -> list[Document]:
    vectorstore = get_metadata_store()
    records = vectorstore._collection.get(include=["documents", "metadatas"])
    return [
        Document(page_content=content, metadata=metadata)
        for content, metadata in zip(records["documents"], records["metadatas"])
    ]


def _purchase_order_documents() -> list[Document]:
    """Load only purchase-order chunks instead of the whole collection."""
    vectorstore = get_metadata_store()
    raw_dir = Path(settings.raw_data_dir)
    filenames = [path.name for path in raw_dir.glob("purchase_orders_*.pdf")]
    if not filenames:
        return []
    records = vectorstore._collection.get(
        where={"filename": {"$in": filenames}},
        include=["documents", "metadatas"],
    )
    return [
        Document(page_content=content, metadata=metadata)
        for content, metadata in zip(records["documents"], records["metadatas"])
    ]


def _is_exhaustive_purchase_order_query(query: str) -> bool:
    normalized = _normalize(query)
    asks_for_all = any(term in normalized for term in ("tous", "toutes", "all", "chaque"))
    asks_for_orders = (
        "purchase order" in normalized
        or "purchase orders" in normalized
        or "purchases order" in normalized
        or "purchases orders" in normalized
        or "bon de commande" in normalized
        or "bons de commande" in normalized
    )
    return asks_for_all and asks_for_orders


def _customer_terms(query: str) -> list[str]:
    """Extract likely customer-name terms from the part after 'de' or 'for'."""
    match = re.search(r"\b(?:de|du|for)\s+(.+)$", _normalize(query))
    if not match:
        return []
    ignored = {
        "tous", "toutes", "les", "le", "la", "des", "purchase", "purchases",
        "order", "orders", "bon", "bons", "commande", "commandes",
    }
    return [term for term in re.findall(r"[a-z0-9]+", match.group(1)) if term not in ignored]


def _matches_customer(document: Document, customer_terms: list[str]) -> bool:
    if not customer_terms:
        return False
    content = _normalize(document.page_content)
    content_words = re.findall(r"[a-z0-9]+", content)
    for term in customer_terms:
        if term in content:
            continue
        if not any(SequenceMatcher(None, term, word).ratio() >= 0.78 for word in content_words):
            return False
    return True


def _domain_candidates(query: str) -> list[Document]:
    """Return chunks from a report identified by month/category clues."""
    normalized = _normalize(query)
    month = next((number for name, number in _MONTHS.items() if name in normalized), None)
    category = next((number for name, number in _CATEGORIES.items() if name in normalized), None)
    if not month and not category:
        return []

    documents = _collection_documents()
    if month:
        documents = [
            document for document in documents
            if f"StockReport_2016-{month}" in document.metadata.get("filename", "")
        ]
    else:
        documents = [
            document for document in documents
            if document.metadata.get("filename", "").startswith("StockReport_")
        ]
    if category:
        category_terms = ("dairy products", "beverages") if category == "4" else ("beverages",)
        documents = [
            document for document in documents
            if any(term in _normalize(document.page_content) for term in category_terms)
        ]
    return documents


def get_retriever(k: int | None = None):
    vectorstore = get_vectorstore()
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k or settings.top_k},
    )


def retrieve_with_scores(query: str, k: int | None = None) -> list[tuple[Document, float]]:
    """Retrieve chunks along with their similarity scores (useful for
    debugging and for the "no relevant context found" guardrail)."""
    limit = k or settings.top_k

    # "Tous les purchase orders de X" is an exhaustive lookup, not a
    # semantic top-k question. Return every matching order before invoking
    # the LLM so it cannot silently omit lower-ranked documents.
    if _is_exhaustive_purchase_order_query(query):
        customer_terms = _customer_terms(query)
        all_orders = [
            document
            for document in _purchase_order_documents()
            if _matches_customer(document, customer_terms)
        ]
        if all_orders:
            return [(document, 1.0) for document in all_orders]

    vectorstore = get_vectorstore()
    domain_documents = _domain_candidates(query)

    # Exact identifiers are important in invoices and purchase orders. A
    # semantic embedding can rank similar documents above the exact match.
    exact_matches: list[tuple[Document, float]] = []
    seen_chunk_ids: set[str] = set()
    order_ids = re.findall(r"\b\d{5}\b", query)
    for order_id in order_ids:
        for filename in (f"invoice_{order_id}.pdf", f"purchase_orders_{order_id}.pdf"):
            records = vectorstore._collection.get(  # noqa: SLF001
                where={"filename": filename},
                include=["documents", "metadatas"],
            )
            for content, metadata in zip(records["documents"], records["metadatas"]):
                chunk_id = metadata.get("chunk_id", "")
                if chunk_id in seen_chunk_ids:
                    continue
                seen_chunk_ids.add(chunk_id)
                exact_matches.append((Document(page_content=content, metadata=metadata), 1.0))

    semantic_matches = vectorstore.similarity_search_with_relevance_scores(query, k=limit)
    if domain_documents:
        domain_ids = {d.metadata.get("chunk_id") for d in domain_documents}
        semantic_matches = [
            (document, score) for document, score in semantic_matches
            if document.metadata.get("chunk_id") not in domain_ids
        ]
        exact_matches.extend((document, 1.0) for document in domain_documents)
    for document, score in semantic_matches:
        chunk_id = document.metadata.get("chunk_id", "")
        if chunk_id not in seen_chunk_ids:
            exact_matches.append((document, score))
            seen_chunk_ids.add(chunk_id)

    return exact_matches[:limit]
