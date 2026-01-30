from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")
    qdrant_url: str = Field(..., alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    redis_url: str = Field(..., alias="REDIS_URL")

    minio_endpoint: str = Field(..., alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(..., alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(..., alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_s3_bucket_prefix: str = Field(default="bioloupe", alias="AWS_S3_BUCKET_PREFIX")

    environment: str = Field(default="development", alias="ENVIRONMENT")
    read_replica_url: str | None = Field(default=None, alias="READ_REPLICA_URL")
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=0, alias="DB_MAX_OVERFLOW")

    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    invitation_token_ttl_hours: int = Field(default=72, alias="INVITATION_TOKEN_TTL_HOURS")

    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    microsoft_client_id: str | None = Field(default=None, alias="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: str | None = Field(default=None, alias="MICROSOFT_CLIENT_SECRET")
    orcid_client_id: str | None = Field(default=None, alias="ORCID_CLIENT_ID")
    orcid_client_secret: str | None = Field(default=None, alias="ORCID_CLIENT_SECRET")
    oauth_redirect_base_url: str = Field(
        default="http://localhost:3000", alias="OAUTH_REDIRECT_BASE_URL"
    )

    audit_log_retention_days: int = Field(
        default=90, alias="AUDIT_LOG_RETENTION_DAYS"
    )
    audit_enable_background_logging: bool = Field(
        default=True, alias="AUDIT_ENABLE_BACKGROUND_LOGGING"
    )

    # Admin seeding
    seed_admin_email: str | None = Field(default=None, alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str | None = Field(default=None, alias="SEED_ADMIN_PASSWORD")

    # WebSocket configuration
    websocket_cors_origins: str = Field(
        default="http://localhost:3000",
        alias="WEBSOCKET_CORS_ORIGINS"
    )
    websocket_ping_timeout: int = Field(
        default=60, alias="WEBSOCKET_PING_TIMEOUT"
    )
    websocket_ping_interval: int = Field(
        default=30, alias="WEBSOCKET_PING_INTERVAL"
    )

    pubmed_search_url: str = Field(
        default="https://api.ncbi.nlm.nih.gov/lit/ctxp/v1/pubmed/", alias="PUBMED_SEARCH_URL"
    )
    arxiv_search_url: str = Field(
        default="http://export.arxiv.org/api/query", alias="ARXIV_SEARCH_URL"
    )
    search_cache_ttl_seconds: int = Field(
        default=300, alias="SEARCH_CACHE_TTL_SECONDS"
    )
    publication_cache_ttl_seconds: int = Field(
        default=900, alias="PUBLICATION_CACHE_TTL_SECONDS"
    )
    slow_query_threshold_ms: int = Field(default=100, alias="SLOW_QUERY_THRESHOLD_MS")
    vector_search_cache_ttl_seconds: int = Field(
        default=300, alias="VECTOR_SEARCH_CACHE_TTL_SECONDS"
    )
    embedding_cache_ttl_seconds: int = Field(
        default=3600, alias="EMBEDDING_CACHE_TTL_SECONDS"
    )
    rate_limit_window_seconds: int = Field(
        default=60, alias="RATE_LIMIT_WINDOW_SECONDS"
    )
    rate_limit_per_user: int = Field(default=60, alias="RATE_LIMIT_PER_USER")
    # AI/LLM configuration
    llm_default_model: str = Field(
        default="gpt-4o-mini", alias="LLM_DEFAULT_MODEL"
    )
    llm_default_temperature: float = Field(
        default=0.7, alias="LLM_DEFAULT_TEMPERATURE"
    )
    llm_default_max_tokens: int = Field(
        default=4000, alias="LLM_DEFAULT_MAX_TOKENS"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
