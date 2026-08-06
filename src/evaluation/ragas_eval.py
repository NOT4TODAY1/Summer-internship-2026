"""
Evaluation module using RAGAS.

Computes the standard RAG quality metrics:
    - faithfulness       : is the answer grounded in the retrieved context? (hallucination proxy)
    - answer_relevancy   : does the answer actually address the question?
    - context_precision  : are the retrieved chunks relevant to the question?
    - context_recall     : did retrieval find all the info needed to answer?

Usage:
    python -m src.evaluation.ragas_eval --testset data/eval/testset.csv

The test set CSV must have columns: question, ground_truth
(ground_truth = the expected/reference answer, written by a human reviewer).
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd
from datasets import Dataset
from langchain_ollama import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

from src.config import settings
from src.rag.pipeline import answer_question
from src.rag.retriever import retrieve_with_scores

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def build_eval_dataset(testset_path: str) -> Dataset:
    """Run the RAG pipeline over a labeled test set and assemble the
    {question, answer, contexts, ground_truth} table RAGAS expects."""
    df = pd.read_csv(testset_path)
    required = {"question", "ground_truth"}
    if not required.issubset(df.columns):
        raise ValueError(f"Test set must contain columns {required}, found {list(df.columns)}")

    records = []
    for _, row in df.iterrows():
        question = row["question"]
        result = answer_question(question)
        contexts = [c for c, _ in retrieve_with_scores(question)]
        records.append(
            {
                "question": question,
                "answer": result.answer,
                "contexts": [c.page_content for c in contexts],
                "ground_truth": row["ground_truth"],
            }
        )
        logger.info("Evaluated: %s", question[:80])

    return Dataset.from_pandas(pd.DataFrame(records))


def run_evaluation(testset_path: str, output_path: str = "docs/ragas_report.json") -> dict:
    dataset = build_eval_dataset(testset_path)

    # Judge LLM + embeddings for RAGAS's own metric computation (kept local via Ollama)
    judge_llm = ChatOllama(base_url=settings.ollama_base_url, model=settings.ollama_model, temperature=0)
    judge_embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)

    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=judge_llm,
        embeddings=judge_embeddings,
    )

    scores = result.to_pandas().mean(numeric_only=True).to_dict()
    logger.info("RAGAS scores: %s", scores)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)

    logger.info("Report saved to %s", output_path)
    return scores


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the RAG pipeline with RAGAS.")
    parser.add_argument("--testset", type=str, default="data/eval/testset.csv")
    parser.add_argument("--output", type=str, default="docs/ragas_report.json")
    args = parser.parse_args()

    run_evaluation(args.testset, args.output)
