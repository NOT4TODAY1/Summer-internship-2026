"""
CLI entry point: run the full ingestion pipeline end-to-end.

Usage:
    python scripts/ingest_documents.py --source data/raw
    python scripts/ingest_documents.py --source data/raw --reset
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.ingestion.loader import load_documents_from_dir
from src.ingestion.chunker import chunk_documents
from src.ingestion.indexer import index_documents, reset_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest company documents into the vector store.")
    parser.add_argument("--source", type=str, default="data/raw", help="Directory containing raw documents.")
    parser.add_argument("--reset", action="store_true", help="Delete the existing collection before ingesting.")
    args = parser.parse_args()

    if args.reset:
        logger.info("Resetting existing collection...")
        reset_index()

    logger.info("Loading documents from %s", args.source)
    documents = load_documents_from_dir(args.source)
    if not documents:
        logger.error("No documents were loaded. Check that %s contains supported files.", args.source)
        return

    logger.info("Chunking %d documents...", len(documents))
    chunks = chunk_documents(documents)

    logger.info("Indexing %d chunks into ChromaDB...", len(chunks))
    count = index_documents(chunks)

    logger.info("Done. %d chunks indexed and ready for querying.", count)


if __name__ == "__main__":
    main()
