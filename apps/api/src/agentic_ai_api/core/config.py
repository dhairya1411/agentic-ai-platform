"""Typed application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with production-only secret safeguards."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "Agentic AI Platform"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    debug: bool = False
    cors_origins: list[str] = Field(default_factory=list)
    database_url: str = "postgresql+asyncpg://agentic_ai:agentic_ai@localhost:5432/agentic_ai"
    database_enabled: bool = True
    jwt_secret_key: SecretStr = SecretStr("local-development-secret-not-for-production")
    encryption_key: SecretStr = SecretStr("local-development-key-not-for-production")
    jwt_issuer: str = "agentic-ai-platform"
    jwt_audience: str = "agentic-ai-web"
    access_token_ttl_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_ttl_days: int = Field(default=30, ge=1, le=90)
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    auth_cookie_secure: bool = False
    openai_api_key: SecretStr = SecretStr("")
    llm_primary_model: str = "gpt-5-mini"
    llm_fallback_model: str = "gpt-4o-mini"
    llm_max_output_tokens: int = Field(default=1_500, ge=64, le=16_000)
    llm_retry_attempts: int = Field(default=2, ge=1, le=4)
    llm_request_timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)
    llm_redact_pii: bool = True
    agent_node_retry_attempts: int = Field(default=3, ge=1, le=5)
    agent_min_confidence: float = Field(default=0.70, ge=0.0, le=1.0)
    agent_auto_approval_confidence: float = Field(default=0.92, ge=0.0, le=1.0)
    qdrant_url: str = "http://localhost:6333"
    memory_collection_name: str = "organization_memory"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = Field(default=1536, ge=1, le=3072)
    memory_default_retention_days: int = Field(default=365, ge=1, le=3650)
    memory_retrieval_candidate_limit: int = Field(default=30, ge=1, le=100)

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Settings:
        """Reject known development values in production-like deployments."""
        if self.app_env in {"staging", "production"}:
            jwt_secret = self.jwt_secret_key.get_secret_value()
            encryption_key = self.encryption_key.get_secret_value()
            if len(jwt_secret) < 32 or jwt_secret.startswith("replace-with") or jwt_secret.startswith("local-"):
                raise ValueError("JWT_SECRET_KEY must be a unique 32+ character deployment secret")
            if len(encryption_key) < 32 or encryption_key.startswith("replace-with") or encryption_key.startswith("local-"):
                raise ValueError("ENCRYPTION_KEY must be supplied by the deployment secret manager")
            if not self.google_client_id or not self.google_client_secret.get_secret_value():
                raise ValueError("Google OAuth credentials are required outside development")
            if not self.openai_api_key.get_secret_value():
                raise ValueError("OPENAI_API_KEY is required outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one immutable settings instance per process."""
    return Settings()
