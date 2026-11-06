"""
Centralized configuration for the RAG Enterprise Assistant.
All values are read from environment variables (.env) with sane defaults,
so the whole pipeline can run out-of-the-box on a laptop with Ollama installed.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM (Ollama) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    ollama_temperature: float = 0.1
    # Limit the generated answer length to reduce time spent waiting for Ollama.
    ollama_num_predict: int = 512
    # Avoid CUDA initialization crashes on machines with an incompatible GPU.
    ollama_num_gpu: int = 0

    # --- Embeddings ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    evaluation_embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    # --- Vector store ---
    chroma_persist_dir: str = str(PROJECT_ROOT / "data" / "processed" / "chroma_db")
    chroma_collection_name: str = "company_documents"

    # --- Chunking ---
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # --- Retrieval ---
    top_k: int = 4

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Paths ---
    raw_data_dir: str = str(PROJECT_ROOT / "data" / "raw")
    processed_data_dir: str = str(PROJECT_ROOT / "data" / "processed")

    # --- MLflow ---
    mlflow_tracking_uri: str = str(PROJECT_ROOT / "mlruns")


settings = Settings()
