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

    jwt_secret_key: str = Field("change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60 * 24, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    invitation_token_ttl_hours: int = Field(72, alias="INVITATION_TOKEN_TTL_HOURS")

    seed_admin_email: str | None = Field(default=None, alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str | None = Field(default=None, alias="SEED_ADMIN_PASSWORD")


@lru_cache
def get_settings() -> Settings:
    return Settings()
