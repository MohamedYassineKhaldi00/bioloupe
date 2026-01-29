"""Model loader with singleton pattern and lazy loading."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from app.core.exceptions import DeviceError, ModelLoadError
from app.core.ml_config import ModelConfig, get_ml_settings, get_model_config
from app.services.embedding.base import BaseEmbeddingService
from app.utils.device_manager import get_device_manager

logger = logging.getLogger(__name__)


class ModelLoader:
    """Singleton model loader with lazy loading and caching."""

    def __init__(self) -> None:
        self._models: dict[str, BaseEmbeddingService] = {}
        self._last_used: dict[str, datetime] = {}
        self._loading_locks: dict[str, asyncio.Lock] = {}
        self.settings = get_ml_settings()
        self.device_manager = get_device_manager()

    async def load_model(self, model_name: str) -> BaseEmbeddingService:
        """Load model with lazy loading.

        Args:
            model_name: Name of model to load

        Returns:
            Loaded embedding service

        Raises:
            ModelLoadError: If model fails to load
        """
        if model_name in self._models:
            self._update_last_used(model_name)
            return self._models[model_name]

        if model_name not in self._loading_locks:
            self._loading_locks[model_name] = asyncio.Lock()

        async with self._loading_locks[model_name]:
            if model_name in self._models:
                self._update_last_used(model_name)
                return self._models[model_name]

            logger.info(f"Loading model: {model_name}")
            service = await self._create_and_load_service(model_name)
            self._models[model_name] = service
            self._update_last_used(model_name)

            logger.info(f"Model loaded: {model_name}")
            return service

    async def _create_and_load_service(
        self, model_name: str
    ) -> BaseEmbeddingService:
        """Create and load embedding service.

        Args:
            model_name: Name of model

        Returns:
            Loaded service

        Raises:
            ModelLoadError: If model fails to load
        """
        config = get_model_config(model_name)
        device = self._select_device(config)
        config = self._update_config_device(config, device)

        service = self._create_service(config)

        try:
            await service.load_model()
            return service
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise ModelLoadError(
                f"Failed to load model {model_name}",
                details={"error": str(e)},
            )

    def _select_device(self, config: ModelConfig) -> str:
        """Select device for model.

        Args:
            config: Model configuration

        Returns:
            Selected device string
        """
        requested_device = (
            config.device
            if config.device != "auto"
            else self.settings.ml_device
        )
        return self.device_manager.select_device(requested_device)

    def _update_config_device(
        self, config: ModelConfig, device: str
    ) -> ModelConfig:
        """Update config with selected device.

        Args:
            config: Original config
            device: Selected device

        Returns:
            Updated config
        """
        return ModelConfig(
            name=config.name,
            model_path=config.model_path,
            embedding_dim=config.embedding_dim,
            max_sequence_length=config.max_sequence_length,
            batch_size=config.batch_size,
            device=device,
            precision=config.precision,
        )

    def _create_service(self, config: ModelConfig) -> BaseEmbeddingService:
        """Create embedding service for model.

        Args:
            config: Model configuration

        Returns:
            Embedding service instance

        Raises:
            ModelLoadError: If service creation fails
        """
        # Import here to avoid circular dependencies
        from app.services.embedding.implementations import (
            get_embedding_service_class,
        )

        service_class = get_embedding_service_class(config.name)
        return service_class(config)

    async def unload_model(self, model_name: str) -> None:
        """Unload model from memory.

        Args:
            model_name: Name of model to unload
        """
        if model_name in self._models:
            logger.info(f"Unloading model: {model_name}")
            del self._models[model_name]
            self._last_used.pop(model_name, None)

    async def unload_unused_models(self) -> None:
        """Unload models that haven't been used recently."""
        if not self.settings.ml_unload_timeout_minutes:
            return

        timeout = timedelta(minutes=self.settings.ml_unload_timeout_minutes)
        now = datetime.now()

        models_to_unload = [
            name
            for name, last_used in self._last_used.items()
            if now - last_used > timeout
        ]

        for model_name in models_to_unload:
            await self.unload_model(model_name)

    async def warmup_models(self, model_names: list[str]) -> None:
        """Warm up models by loading them.

        Args:
            model_names: List of model names to warm up
        """
        if not self.settings.ml_model_warmup:
            return

        logger.info(f"Warming up models: {model_names}")

        for model_name in model_names:
            try:
                await self.load_model(model_name)
            except Exception as e:
                logger.error(f"Failed to warm up model {model_name}: {e}")

    def get_loaded_models(self) -> list[str]:
        """Get list of loaded model names.

        Returns:
            List of loaded model names
        """
        return list(self._models.keys())

    def is_model_loaded(self, model_name: str) -> bool:
        """Check if model is loaded.

        Args:
            model_name: Model name

        Returns:
            True if model is loaded
        """
        return model_name in self._models

    def _update_last_used(self, model_name: str) -> None:
        """Update last used timestamp for model.

        Args:
            model_name: Model name
        """
        self._last_used[model_name] = datetime.now()


_model_loader: ModelLoader | None = None


def get_model_loader() -> ModelLoader:
    """Get singleton model loader instance.

    Returns:
        ModelLoader instance
    """
    global _model_loader
    if _model_loader is None:
        _model_loader = ModelLoader()
    return _model_loader
