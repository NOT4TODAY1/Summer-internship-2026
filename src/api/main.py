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

from fastapi import FastAPI, HTTPException
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
        sources=[SourceItem(**s) for s in result.sources],
        context_found=result.context_found,
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
