.PHONY: install ingest api ui eval test docker-up docker-down

install:
	pip install -r requirements.txt

# Pull the local LLM once (requires Ollama installed: https://ollama.com)
pull-model:
	ollama pull mistral

ingest:
	python scripts/ingest_documents.py --source data/raw --reset

api:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

ui:
	streamlit run src/app/streamlit_app.py

eval:
	python -m src.evaluation.ragas_eval --testset data/eval/testset.csv

test:
	pytest tests/ -v

docker-up:
	docker compose up --build

docker-down:
	docker compose down
