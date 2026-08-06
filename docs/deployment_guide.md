# Guide de Déploiement

## Option A — Déploiement local (développement)

```bash
# 1. Environnement Python
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. LLM local
# Installer Ollama : https://ollama.com/download
ollama pull mistral
ollama serve &

# 3. Config
cp .env.example .env

# 4. Données
# Placer le dataset (dézippé) dans data/raw/
python scripts/ingest_documents.py --source data/raw --reset

# 5. Services
uvicorn src.api.main:app --reload &      # http://localhost:8000/docs
streamlit run src/app/streamlit_app.py    # http://localhost:8501
```

## Option B — Déploiement Docker (recommandé pour la démo / soutenance)

```bash
docker compose up --build -d
docker exec -it rag-ollama ollama pull mistral
```

Puis, pour ingérer les documents (une fois les conteneurs démarrés) :
```bash
curl -X POST http://localhost:8000/ingest -H "Content-Type: application/json" -d '{"reset": true}'
```

Services exposés :
- **API** : http://localhost:8000/docs (Swagger UI auto-généré)
- **UI** : http://localhost:8501

Pour arrêter :
```bash
docker compose down
```

## Option C — Déploiement serveur (production légère)

1. Provisionner une VM (4 vCPU / 16 Go RAM minimum recommandé pour Mistral 7B en CPU ; un GPU accélère nettement l'inférence).
2. Installer Docker + Docker Compose.
3. Cloner le repo, copier `.env.example` → `.env`, ajuster les valeurs (ports, modèle).
4. `docker compose up --build -d`
5. Mettre un reverse proxy (nginx/Traefik) devant le port 8501 (UI) avec HTTPS/authentification si exposé publiquement — **l'API et l'UI n'ont pas d'authentification native**, à ajouter avant toute exposition sur Internet.
6. Automatiser l'ingestion périodique (cron / MLflow job) si le corpus documentaire évolue.

## Sécurité — points d'attention avant mise en production

- Ajouter une authentification (API key, OAuth) sur les endpoints FastAPI.
- Restreindre l'accès réseau à ChromaDB et Ollama (ne pas les exposer publiquement).
- Anonymiser/filtrer les documents sensibles avant ingestion si nécessaire (RGPD).
- Journaliser les requêtes pour audit (qui a demandé quoi, quelles sources ont été utilisées).

## Suivi des expériences (MLflow)

```bash
mlflow ui --backend-store-uri ./mlruns
```
Permet de tracer, au fil des itérations, les paramètres (chunk_size, top_k, modèle LLM) et les scores RAGAS associés — utile pour justifier les choix dans le rapport de stage.
