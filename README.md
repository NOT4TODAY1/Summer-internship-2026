# 📚 Assistant Documentaire Interne — Système RAG

Système de **Retrieval-Augmented Generation (RAG)** permettant d'interroger en
langage naturel les documents internes d'une entreprise (rapports, procédures,
contrats, manuels...), avec réponses **sourcées** et générées par un LLM
**local et gratuit** (via [Ollama](https://ollama.com)).

Projet réalisé dans le cadre d'un stage Data Science (Été 2026), à partir du
dataset [Company Documents Dataset](https://www.kaggle.com/datasets/ayoubcherguelaine/company-documents-dataset) (Kaggle).

---

## 🏗️ Architecture

```
                    ┌─────────────────┐
   Documents  ───▶  │   Ingestion      │  (PDF, DOCX, TXT, MD)
   (data/raw/)      │  load → chunk    │
                    └────────┬─────────┘
                             ▼
                    ┌─────────────────┐
                    │  Embeddings      │  sentence-transformers
                    │  (local, free)   │
                    └────────┬─────────┘
                             ▼
                    ┌─────────────────┐
                    │   ChromaDB       │  vector store (persisted)
                    └────────┬─────────┘
                             ▼
   Question  ───▶   ┌─────────────────┐      ┌────────────────┐
   (Streamlit) ───▶ │  Retriever       │ ───▶ │  Ollama LLM     │
                    │  (top-k search)  │      │ (Mistral/LLaMA) │
                    └────────┬─────────┘      └───────┬────────┘
                             ▼                         ▼
                    ┌──────────────────────────────────────┐
                    │   Réponse sourcée (FastAPI /query)    │
                    └────────────────────────────────────────┘
```

See [`docs/architecture.md`](docs/architecture.md) for the full breakdown.

---

## 🚀 Quickstart (local, no Docker)

### 1. Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) installed locally

### 2. Install & pull the LLM
```bash
make install
make pull-model        # downloads Mistral 7B (~4GB)
ollama serve            # keep this running in a separate terminal
```

### 3. Add your documents
Download the dataset from Kaggle and unzip it into `data/raw/`:
```
data/raw/
├── invoices/
├── contracts/
├── reports/
└── ...
```
(Or drop in your own company PDFs/DOCX/TXT files — any mix is supported.)

### 4. Ingest & index
```bash
cp .env.example .env
make ingest
```

### 5. Run the API + UI
```bash
make api      # terminal 1 → http://localhost:8000/docs
make ui       # terminal 2 → http://localhost:8501
```

---

## 🐳 Quickstart (Docker)

```bash
docker compose up --build
# then, in another terminal, pull the model into the running ollama container:
docker exec -it rag-ollama ollama pull mistral
```
- API: http://localhost:8000/docs
- UI: http://localhost:8501

---

## 📊 Evaluation (RAGAS)

Fill in `data/eval/testset.csv` with real questions + expected answers from
your document set, then run:
```bash
make eval
```
This produces `docs/ragas_report.json` with **faithfulness**,
**answer_relevancy**, **context_precision**, and **context_recall** scores —
the core metrics for measuring hallucination and retrieval quality.

---

## 🧪 Tests
```bash
make test
```

---

## 📁 Project structure

```
rag-enterprise-assistant/
├── src/
│   ├── config.py              # centralized settings (.env driven)
│   ├── ingestion/
│   │   ├── loader.py          # PDF/DOCX/TXT/MD loading
│   │   ├── chunker.py         # text splitting
│   │   └── indexer.py         # embeddings + ChromaDB
│   ├── rag/
│   │   ├── retriever.py       # semantic search
│   │   ├── generator.py       # Ollama LLM wrapper
│   │   └── pipeline.py        # retrieval + prompt + generation
│   ├── evaluation/
│   │   └── ragas_eval.py      # RAGAS quality metrics
│   ├── api/
│   │   └── main.py            # FastAPI backend
│   └── app/
│       └── streamlit_app.py   # chat UI
├── scripts/
│   └── ingest_documents.py    # CLI ingestion entry point
├── data/
│   ├── raw/                   # place the Kaggle dataset here
│   ├── processed/             # ChromaDB persisted index
│   └── eval/testset.csv       # RAGAS evaluation questions
├── tests/
├── docs/
│   ├── architecture.md
│   └── deployment_guide.md
├── Dockerfile.api
├── Dockerfile.streamlit
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

---

## 🔧 Tech stack

| Composant | Choix |
|---|---|
| Langage | Python 3.11+ |
| Orchestration RAG | LangChain |
| LLM | Ollama (Mistral 7B / LLaMA 3) — **local, gratuit** |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Base vectorielle | ChromaDB |
| Évaluation | RAGAS |
| API | FastAPI |
| Interface | Streamlit |
| Déploiement | Docker / docker-compose |
| Versioning | Git, MLflow (optionnel) |

---

## 🗺️ Roadmap suggérée (2 mois)

| Semaine | Objectif |
|---|---|
| 1–2 | Ingestion & nettoyage du dataset Kaggle, pipeline de chunking |
| 3–4 | Indexation vectorielle, tuning du retriever (k, chunk size) |
| 5 | Intégration LLM (Ollama) + prompt engineering anti-hallucination |
| 6 | Évaluation RAGAS, itération sur la qualité |
| 7 | API FastAPI + interface Streamlit |
| 8 | Dockerisation, documentation, rapport de stage & soutenance |

---

## 📄 License / Data

Dataset source: [Company Documents Dataset](https://www.kaggle.com/datasets/ayoubcherguelaine/company-documents-dataset) — subject to its own Kaggle license terms. Check the dataset card before any external/commercial use.
