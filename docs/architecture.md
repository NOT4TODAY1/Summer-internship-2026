# Architecture Technique

## 1. Vue d'ensemble

Le système suit le pattern RAG classique en deux phases découplées :

1. **Phase offline (ingestion)** : documents bruts → texte → chunks → embeddings → index vectoriel persisté.
2. **Phase online (interrogation)** : question → embedding de la question → recherche de similarité (top-k) → construction du prompt avec contexte → génération de la réponse par le LLM.

Les deux phases sont découplées : on ré-ingère les documents seulement quand
le corpus change, alors que l'interrogation est en temps réel.

## 2. Composants

### 2.1 Ingestion (`src/ingestion/`)
- **loader.py** : normalise PDF (`pypdf`), DOCX (`python-docx`), TXT/MD/CSV en `Document` LangChain avec métadonnées (`source`, `filename`, `file_type`, `ingested_at`).
- **chunker.py** : `RecursiveCharacterTextSplitter` (taille configurable, défaut 1000 caractères / 150 de chevauchement). Le chevauchement évite de couper une information au milieu de deux chunks.
- **indexer.py** : embeddings via `sentence-transformers/all-MiniLM-L6-v2` (rapide, léger, tourne sur CPU), stockage persistant dans ChromaDB.

### 2.2 RAG (`src/rag/`)
- **retriever.py** : recherche par similarité cosinus (top-k configurable, défaut k=4), avec scores de pertinence exposés pour le débogage et les garde-fous.
- **generator.py** : wrapper autour d'Ollama (`ChatOllama`), modèle configurable via variable d'environnement (`mistral`, `llama3`, etc.).
- **pipeline.py** : assemble contexte + question dans un prompt système strict qui interdit explicitement au LLM d'inventer des faits hors contexte — c'est le principal levier anti-hallucination au niveau prompt.

### 2.3 Évaluation (`src/evaluation/`)
- **ragas_eval.py** : calcule 4 métriques RAGAS sur un jeu de test annoté :
  - **faithfulness** : la réponse est-elle fidèle au contexte récupéré ? (mesure directe des hallucinations)
  - **answer_relevancy** : la réponse adresse-t-elle la question posée ?
  - **context_precision** : les chunks récupérés sont-ils pertinents ?
  - **context_recall** : le retriever a-t-il trouvé toute l'information nécessaire ?

### 2.4 Service (`src/api/`, `src/app/`)
- **FastAPI** expose `/query`, `/ingest`, `/health`, `/collection/info`. C'est la seule interface entre le modèle et le monde extérieur — ce découplage permet de brancher n'importe quel frontend (Streamlit, Slack bot, etc.) sans toucher au cœur RAG.
- **Streamlit** consomme l'API HTTP, affiche les sources utilisées pour chaque réponse (transparence / traçabilité), et permet de relancer l'ingestion depuis l'UI.

## 3. Pourquoi ces choix techniques ?

| Choix | Justification |
|---|---|
| ChromaDB plutôt que Pinecone/Qdrant | 100% local, pas de compte/API key externe, suffisant jusqu'à plusieurs centaines de milliers de chunks |
| Ollama plutôt que GPT-4o | Aucun coût d'API, données ne quittent jamais l'infrastructure (confidentialité des documents internes), contrôle total sur le modèle déployé |
| sentence-transformers plutôt que `text-embedding-ada-002` | Cohérent avec le choix "tout local", pas de coût récurrent |
| API/UI découplées | Permet de déployer le moteur RAG derrière n'importe quelle interface (web, Slack, Teams) sans réécrire la logique cœur |

## 4. Limites connues & pistes d'amélioration

- **Latence** : un LLM local sur CPU peut être plus lent qu'une API cloud — envisager un GPU ou un modèle quantisé plus petit (ex. `mistral:7b-instruct-q4`) si la latence est critique.
- **Qualité d'extraction PDF** : `pypdf` ne gère pas l'OCR — les PDF scannés (images) nécessiteront un ajout d'OCR (ex. `unstructured` avec `hi_res` ou `pytesseract`).
- **Chunking naïf** : le découpage récursif ne comprend pas la structure du document (tableaux, titres) — un chunking sémantique ou basé sur la mise en page pourrait améliorer la précision pour les documents très structurés.
- **Pas de re-ranking** : ajouter un cross-encoder de re-ranking après la recherche vectorielle améliorerait `context_precision`.
