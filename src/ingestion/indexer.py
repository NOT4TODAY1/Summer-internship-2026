"""
Indexing module.

Generates sentence-embedding vectors for document chunks and persists
them in a local ChromaDB collection. Fully local — no external API key
required (uses sentence-transformers under the hood).
"""
from __future__ import annotations

import logging

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.config import settings

logger = logging.getLogger(__name__)

_embeddings_instance: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Lazily instantiate the embedding model (loaded once, reused)."""
    global _embeddings_instance
    if _embeddings_instance is None:
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings_instance


def get_vectorstore() -> Chroma:
    """Return a handle to the persisted Chroma collection."""
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


def get_metadata_store() -> Chroma:
    """Return a Chroma handle for metadata/document reads without embeddings."""
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=None,
        persist_directory=settings.chroma_persist_dir,
    )


def index_documents(chunks: list[Document], batch_size: int = 128) -> int:
    """Embed and persist chunks into ChromaDB. Returns number of chunks indexed."""
    if not chunks:
        logger.warning("No chunks to index.")
        return 0

    vectorstore = get_vectorstore()

    total = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vectorstore.add_documents(batch)
        total += len(batch)
        logger.info("Indexed %d/%d chunks", total, len(chunks))

    logger.info("Indexing complete: %d chunks persisted to %s", total, settings.chroma_persist_dir)
    return total


def reset_index() -> None:
    """Delete the existing collection (useful for re-ingestion)."""
    vectorstore = get_vectorstore()
    vectorstore.delete_collection()
    logger.info("Collection '%s' deleted.", settings.chroma_collection_name)
