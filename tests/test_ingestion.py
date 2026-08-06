"""
Sanity tests for the ingestion pipeline.
Run with: pytest tests/ -v
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document

from src.ingestion.chunker import chunk_documents


def test_chunking_splits_long_document():
    long_text = "Ceci est une phrase de test. " * 500
    doc = Document(page_content=long_text, metadata={"source": "test.txt", "filename": "test.txt"})

    chunks = chunk_documents([doc], chunk_size=200, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(c.metadata.get("chunk_id") for c in chunks)
    assert all(c.metadata["source"] == "test.txt" for c in chunks)


def test_chunking_preserves_short_document():
    short_text = "Texte court qui tient dans un seul chunk."
    doc = Document(page_content=short_text, metadata={"source": "short.txt", "filename": "short.txt"})

    chunks = chunk_documents([doc], chunk_size=1000, chunk_overlap=100)

    assert len(chunks) == 1
    assert chunks[0].page_content.strip() == short_text
