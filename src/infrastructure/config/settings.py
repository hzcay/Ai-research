from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "research_chunks"
    embed_model_name: str = "BAAI/bge-m3"

    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 86400

    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/ai_research"
    
    minio_url: str = "minio:9000"
    minio_access_key: str = "admin"
    minio_secret_key: str = "password"
    minio_bucket: str = "ai-research"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_model_2: str = "llama-3.1-8b-instant"
    groq_timeout_s: float = 30.0
    groq_retries: int = 2

    qdrant_timeout_s: float = 10.0
    qdrant_retries: int = 2

    upload_dir: str = "data/uploads"

    hybrid_enabled: bool = True
    hybrid_alpha: float = 0.7
    hybrid_beta: float = 0.3
    lexical_candidate_limit: int = 1000

    rerank_enabled: bool = True
    rerank_top_n: int = 20
    rerank_final_k: int = 5

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
