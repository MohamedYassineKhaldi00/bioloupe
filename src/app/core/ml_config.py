"""ML model configurations for embedding services."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MLSettings(BaseSettings):
    """Machine learning settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ml_models_cache_dir: str = Field(
        default="/tmp/ml_models", alias="ML_MODELS_CACHE_DIR"
    )
    ml_device: str = Field(default="auto", alias="ML_DEVICE")
    ml_enable_caching: bool = Field(default=True, alias="ML_ENABLE_CACHING")
    ml_batch_size: int = Field(default=32, alias="ML_BATCH_SIZE")
    ml_cache_ttl_seconds: int = Field(default=3600, alias="ML_CACHE_TTL_SECONDS")
    ml_model_warmup: bool = Field(default=False, alias="ML_MODEL_WARMUP")
    ml_precision: str = Field(default="float32", alias="ML_PRECISION")
    ml_unload_timeout_minutes: int = Field(
        default=30, alias="ML_UNLOAD_TIMEOUT_MINUTES"
    )


@lru_cache
def get_ml_settings() -> MLSettings:
    """Get cached ML settings instance."""
    return MLSettings()


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for an embedding model."""

    name: str
    model_path: str
    embedding_dim: int
    max_sequence_length: int
    batch_size: int
    device: str
    precision: Literal["float32", "float16", "int8"]


# Predefined model configurations
SPECTER2_CONFIG = ModelConfig(
    name="specter2",
    model_path="allenai/specter2",
    embedding_dim=768,
    max_sequence_length=512,
    batch_size=32,
    device="auto",
    precision="float32",
)

ESM2_CONFIG = ModelConfig(
    name="esm2",
    model_path="facebook/esm2_t33_650M_UR50D",
    embedding_dim=1280,
    max_sequence_length=1024,
    batch_size=16,
    device="auto",
    precision="float32",
)

CLIP_CONFIG = ModelConfig(
    name="clip",
    model_path="openai/clip-vit-base-patch32",
    embedding_dim=512,
    max_sequence_length=77,
    batch_size=32,
    device="auto",
    precision="float32",
)

PAPER_EMBEDDING_CONFIG = ModelConfig(
    name="paper_embedding",
    model_path="allenai/specter2",
    embedding_dim=768,
    max_sequence_length=512,
    batch_size=16,
    device="auto",
    precision="float32",
)

SEQUENCE_EMBEDDING_CONFIG = ModelConfig(
    name="sequence_embedding",
    model_path="facebook/esm2_t33_650M_UR50D",
    embedding_dim=1280,
    max_sequence_length=1024,
    batch_size=8,
    device="auto",
    precision="float32",
)

IMAGE_EMBEDDING_CONFIG = ModelConfig(
    name="image_embedding",
    model_path="openai/clip-vit-base-patch32",
    embedding_dim=512,
    max_sequence_length=77,
    batch_size=32,
    device="auto",
    precision="float32",
)


MODEL_REGISTRY = {
    "specter2": SPECTER2_CONFIG,
    "esm2": ESM2_CONFIG,
    "clip": CLIP_CONFIG,
    "paper_embedding": PAPER_EMBEDDING_CONFIG,
    "sequence_embedding": SEQUENCE_EMBEDDING_CONFIG,
    "image_embedding": IMAGE_EMBEDDING_CONFIG,
}


def get_model_config(model_name: str) -> ModelConfig:
    """Get configuration for a specific model.

    Args:
        model_name: Name of the model

    Returns:
        Model configuration

    Raises:
        ValueError: If model not found in registry
    """
    if model_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Model '{model_name}' not found. "
            f"Available: {list(MODEL_REGISTRY.keys())}"
        )
    return MODEL_REGISTRY[model_name]
