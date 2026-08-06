"""
Chunking module.

Splits long documents into overlapping chunks sized for the embedding
model's context window, while preserving traceable metadata (chunk index,
parent source) on every chunk for citation purposes.
"""
from __future__ import annotations

import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import settings

logger = logging.getLogger(__name__)


def chunk_documents(
    documents: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """Split documents into chunks, tagging each with a chunk_id."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)

    # Add a stable, human-readable chunk id per source document
    counters: dict[str, int] = {}
    for chunk in chunks:
        src = chunk.metadata.get("source", "unknown")
        counters[src] = counters.get(src, 0) + 1
        chunk.metadata["chunk_id"] = f"{chunk.metadata.get('filename', src)}::chunk_{counters[src]}"

    logger.info("Split %d documents into %d chunks", len(documents), len(chunks))
    return chunks
