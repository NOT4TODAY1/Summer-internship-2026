"""
Document loading module.

Handles heterogeneous company documents (PDF, DOCX, TXT, MD, CSV) and
normalizes them into LangChain `Document` objects with rich metadata
(source path, file type, ingestion timestamp) so results can always
be traced back to their origin — required for "sourced answers".
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader
from docx import Document as DocxDocument

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}


def _load_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages)


def _load_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


_LOADERS = {
    ".pdf": _load_pdf,
    ".docx": _load_docx,
    ".txt": _load_text,
    ".md": _load_text,
    ".csv": _load_text,
}


def load_document(path: Path) -> Document | None:
    """Load a single file into a LangChain Document with metadata."""
    ext = path.suffix.lower()
    if ext not in _LOADERS:
        logger.warning("Skipping unsupported file type: %s", path)
        return None

    try:
        content = _LOADERS[ext](path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load %s: %s", path, exc)
        return None

    if not content or not content.strip():
        logger.warning("No extractable text in %s", path)
        return None

    metadata = {
        "source": str(path),
        "filename": path.name,
        "file_type": ext.lstrip("."),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    return Document(page_content=content, metadata=metadata)


def load_documents_from_dir(directory: str | Path) -> list[Document]:
    """Recursively load every supported document under `directory`."""
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Data directory not found: {directory}")

    documents: list[Document] = []
    files = [p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]

    logger.info("Found %d candidate files under %s", len(files), directory)

    for path in files:
        doc = load_document(path)
        if doc is not None:
            documents.append(doc)

    logger.info("Successfully loaded %d/%d documents", len(documents), len(files))
    return documents
