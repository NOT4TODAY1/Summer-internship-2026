"""
FastAPI backend for the RAG Enterprise Assistant.

Endpoints:
    GET  /health          -> liveness check
    POST /query           -> ask a question, get a sourced answer
    POST /ingest          -> trigger (re-)ingestion of data/raw
    GET  /collection/info -> basic stats about the vector store
"""
from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from src.config import settings
from src.ingestion.chunker import chunk_documents
from src.ingestion.indexer import get_vectorstore, index_documents, reset_index
from src.ingestion.loader import load_documents_from_dir
from src.rag.pipeline import answer_question

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Enterprise Assistant API",
    description="Internal document search & Q&A powered by Retrieval-Augmented Generation.",
    version="1.0.0",
)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["Quelle est la procédure de remboursement des notes de frais ?"])
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceItem(BaseModel):
    filename: str | None
    chunk_id: str | None
    relevance_score: float
    excerpt: str | None = None
    document_url: str | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    context_found: bool


class IngestRequest(BaseModel):
    source_dir: str = Field(default=settings.raw_data_dir)
    reset: bool = Field(default=False)


class IngestResponse(BaseModel):
    documents_loaded: int
    chunks_indexed: int


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    try:
        result = answer_question(req.question, k=req.top_k)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return QueryResponse(
        answer=result.answer,
        sources=[
            SourceItem(
                **s,
                document_url=(
                    f"/documents/{quote(s['filename'])}" if s.get("filename") else None
                ),
            )
            for s in result.sources
        ],
        context_found=result.context_found,
    )


def _document_path(filename: str) -> Path:
    """Resolve a document inside the configured data directory only."""
    data_dir = Path(settings.raw_data_dir).resolve()
    candidate = (data_dir / filename).resolve()
    if data_dir not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Document introuvable.")
    if candidate.suffix.lower() not in {".pdf", ".docx", ".txt", ".md", ".csv"}:
        raise HTTPException(status_code=404, detail="Type de document non pris en charge.")
    return candidate


@app.get("/documents/{filename:path}/text", response_class=PlainTextResponse)
def get_document_text(filename: str) -> str:
    """Return a readable text preview for non-PDF source documents."""
    path = _document_path(filename)
    if path.suffix.lower() not in {".txt", ".md", ".csv"}:
        raise HTTPException(status_code=415, detail="Aperçu texte indisponible pour ce type de document.")
    return path.read_text(encoding="utf-8", errors="ignore")


@app.get("/documents/{filename:path}")
def get_document(filename: str) -> FileResponse:
    """Open or download a source document without allowing path traversal."""
    path = _document_path(filename)
    media_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }
    return FileResponse(
        path,
        media_type=media_types[path.suffix.lower()],
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )


@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest) -> IngestResponse:
    try:
        if req.reset:
            reset_index()

        documents = load_documents_from_dir(req.source_dir)
        if not documents:
            raise HTTPException(status_code=400, detail=f"No supported documents found in {req.source_dir}")

        chunks = chunk_documents(documents)
        count = index_documents(chunks)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return IngestResponse(documents_loaded=len(documents), chunks_indexed=count)


@app.get("/collection/info")
def collection_info() -> dict:
    vectorstore = get_vectorstore()
    try:
        count = vectorstore._collection.count()  # noqa: SLF001
    except Exception:  # noqa: BLE001
        count = None
    return {
        "collection_name": settings.chroma_collection_name,
        "chunk_count": count,
        "embedding_model": settings.embedding_model,
        "llm_model": settings.ollama_model,
    }
