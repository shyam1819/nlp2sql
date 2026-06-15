"""Application settings, loaded from environment / .env.

Everything that varies between environments (model, db paths, retry budget,
cache backend) lives here so nodes and services stay configuration-free.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # LangSmith tracing/observability (optional)
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "nlp2sql"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    # Database under query (opened read-only)
    db_path: str = "data/sakila.db"

    # Agent behaviour — shared retry budget for Node 6 (guard) and Node 7 (execute)
    max_retries: int = 2

    # Cache for table schemas + descriptions
    cache_backend: str = "memory"  # memory | redis
    redis_url: str = "redis://localhost:6379/0"

    # Conversation persistence
    checkpoint_db_path: str = "data/checkpoints.db"
    conversation_db_path: str = "data/conversations.db"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so the .env is parsed once per process."""
    return Settings()
