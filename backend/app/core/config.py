from functools import lru_cache
from typing import Literal, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "DEVA INTELLIGENCE"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = True
    TESTING: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://deva_user:deva_password@postgres:5432/deva_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis & Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # MLflow Tracking
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"

    # Security & Auth
    SECRET_KEY: str = "deva-intelligence-super-secret-key-change-in-production-2026-phase1"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # LLM Settings
    LLM_PROVIDER: Literal["openai_compatible", "mock"] = "mock"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = "mock-api-key"
    LLM_MODEL_PRIMARY: str = "gpt-4o"
    LLM_MODEL_FAST: str = "gpt-4o-mini"

    # Embedding & Reranker Settings
    EMBEDDING_MODEL: str = "BAAI/bge-base-en-v1.5"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    EMBEDDING_DIM: int = 768

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            val = v.strip().lower()
            if val in ("true", "1", "yes", "t", "dev", "development"):
                return True
            if val in ("false", "0", "no", "f", "release", "prod", "production"):
                return False
        return bool(v)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
