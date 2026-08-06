"""
RAG pipeline orchestration.

Ties retrieval and generation together with a prompt explicitly
instructed to (a) answer only from the provided context and
(b) say "I don't know" rather than invent facts — the main
prompt-level lever against hallucination, complemented by the
RAGAS evaluation in src/evaluation/.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from src.rag.generator import get_llm
from src.rag.retriever import get_retriever, retrieve_with_scores

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un assistant interne d'entreprise. Réponds UNIQUEMENT à partir \
du contexte fourni ci-dessous, extrait des documents internes de l'entreprise.

Règles strictes :
- Si la réponse ne se trouve pas dans le contexte, réponds explicitement : \
"Je ne trouve pas cette information dans les documents disponibles."
- Ne jamais inventer de faits, chiffres ou procédures qui ne sont pas dans le contexte.
- Cite les documents sources utilisés (nom de fichier) à la fin de ta réponse.
- Réponds de façon concise et professionnelle, en français, sauf si la question est posée en anglais.

Contexte :
{context}

Question : {question}

Réponse :"""

_prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)


def _format_docs(docs) -> str:
    return "\n\n---\n\n".join(
        f"[Source: {d.metadata.get('filename', 'unknown')}]\n{d.page_content}" for d in docs
    )


@dataclass
class RAGResponse:
    answer: str
    sources: list[dict] = field(default_factory=list)
    context_found: bool = True


def answer_question(question: str, k: int | None = None) -> RAGResponse:
    """Run the full retrieve -> augment -> generate pipeline for a question."""
    scored_docs = retrieve_with_scores(question, k=k)

    if not scored_docs:
        return RAGResponse(
            answer="Je ne trouve pas cette information dans les documents disponibles.",
            sources=[],
            context_found=False,
        )

    docs = [d for d, _score in scored_docs]

    chain = (
        {"context": lambda x: _format_docs(docs), "question": RunnablePassthrough()}
        | _prompt
        | get_llm()
        | StrOutputParser()
    )

    answer = chain.invoke(question)

    sources = [
        {
            "filename": d.metadata.get("filename"),
            "chunk_id": d.metadata.get("chunk_id"),
            "relevance_score": round(float(score), 3),
        }
        for d, score in scored_docs
    ]

    return RAGResponse(answer=answer, sources=sources, context_found=True)
