"""
Generation module.

Wraps the local Ollama LLM (Mistral / LLaMA 3 / etc.) behind a single
`get_llm()` factory, so swapping models only means changing the
OLLAMA_MODEL env var — no code changes needed.

Prerequisite: Ollama must be installed and running locally, with the
target model pulled, e.g.:
    ollama pull mistral
    ollama serve
"""
from __future__ import annotations

from langchain_ollama import ChatOllama

from src.config import settings

_llm_instance: ChatOllama | None = None


def get_llm() -> ChatOllama:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=settings.ollama_temperature,
            num_predict=settings.ollama_num_predict,
            num_gpu=settings.ollama_num_gpu,
        )
    return _llm_instance
