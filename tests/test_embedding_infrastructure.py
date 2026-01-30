"""Tests for embedding infrastructure."""

from __future__ import annotations

import numpy as np
import pytest

from app.core.exceptions import EmbeddingError, ModelLoadError
from app.core.ml_config import get_model_config
from app.services.embedding import get_model_loader
from app.utils.device_manager import get_device_manager


class TestDeviceManager:
    """Test device manager functionality."""

    def test_cuda_detection(self) -> None:
        """Test CUDA availability detection."""
        device_manager = get_device_manager()
        is_available = device_manager.is_cuda_available()
        assert isinstance(is_available, bool)

    def test_device_selection_auto(self) -> None:
        """Test automatic device selection."""
        device_manager = get_device_manager()
        device = device_manager.select_device("auto")
        assert device in ["cpu", "cuda:0"]

    def test_device_selection_cpu(self) -> None:
        """Test CPU device selection."""
        device_manager = get_device_manager()
        device = device_manager.select_device("cpu")
        assert device == "cpu"

    def test_device_count(self) -> None:
        """Test CUDA device count."""
        device_manager = get_device_manager()
        count = device_manager.get_cuda_device_count()
        assert isinstance(count, int)
        assert count >= 0

    def test_memory_info_cpu(self) -> None:
        """Test CPU memory information."""
        device_manager = get_device_manager()
        memory_info = device_manager.get_device_memory_info("cpu")
        assert "total" in memory_info
        assert "available" in memory_info
        assert memory_info["total"] > 0


class TestModelConfig:
    """Test model configuration."""

    def test_get_specter2_config(self) -> None:
        """Test SPECTER2 configuration."""
        config = get_model_config("specter2")
        assert config.name == "specter2"
        assert config.embedding_dim == 768
        assert config.max_sequence_length == 512

    def test_get_esm2_config(self) -> None:
        """Test ESM-2 configuration."""
        config = get_model_config("esm2")
        assert config.name == "esm2"
        assert config.embedding_dim == 1280
        assert config.max_sequence_length == 1024

    def test_get_clip_config(self) -> None:
        """Test CLIP configuration."""
        config = get_model_config("clip")
        assert config.name == "clip"
        assert config.embedding_dim == 512
        assert config.max_sequence_length == 77

    def test_invalid_model_config(self) -> None:
        """Test invalid model configuration."""
        with pytest.raises(ValueError, match="not found"):
            get_model_config("invalid_model")


class TestModelLoader:
    """Test model loader functionality."""

    @pytest.mark.asyncio
    async def test_load_model(self) -> None:
        """Test loading a model."""
        model_loader = get_model_loader()

        # Note: This test may fail if models not downloaded
        # or dependencies not installed
        try:
            service = await model_loader.load_model("specter2")
            assert service is not None
            assert service.model_name == "specter2"
            assert service.is_loaded
        except ModelLoadError:
            pytest.skip("Model loading requires dependencies")

    @pytest.mark.asyncio
    async def test_model_singleton(self) -> None:
        """Test model singleton behavior."""
        model_loader = get_model_loader()

        try:
            service1 = await model_loader.load_model("specter2")
            service2 = await model_loader.load_model("specter2")
            assert service1 is service2
        except ModelLoadError:
            pytest.skip("Model loading requires dependencies")

    @pytest.mark.asyncio
    async def test_get_loaded_models(self) -> None:
        """Test getting loaded models."""
        model_loader = get_model_loader()
        loaded = model_loader.get_loaded_models()
        assert isinstance(loaded, list)

    @pytest.mark.asyncio
    async def test_is_model_loaded(self) -> None:
        """Test checking if model is loaded."""
        model_loader = get_model_loader()
        is_loaded = model_loader.is_model_loaded("specter2")
        assert isinstance(is_loaded, bool)

    @pytest.mark.asyncio
    async def test_unload_model(self) -> None:
        """Test unloading a model."""
        model_loader = get_model_loader()

        try:
            await model_loader.load_model("specter2")
            await model_loader.unload_model("specter2")
            assert not model_loader.is_model_loaded("specter2")
        except ModelLoadError:
            pytest.skip("Model loading requires dependencies")


@pytest.mark.skipif(
    condition=True,
    reason="Integration tests require ML dependencies installed",
)
class TestEmbeddingServices:
    """Integration tests for embedding services."""

    @pytest.mark.asyncio
    async def test_specter2_embed(self) -> None:
        """Test SPECTER2 embedding generation."""
        model_loader = get_model_loader()
        service = await model_loader.load_model("specter2")

        text = "Machine learning for protein structure prediction"
        embedding = await service.embed(text)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)

    @pytest.mark.asyncio
    async def test_specter2_embed_batch(self) -> None:
        """Test SPECTER2 batch embedding."""
        model_loader = get_model_loader()
        service = await model_loader.load_model("specter2")

        texts = [
            "First paper about biology",
            "Second paper about chemistry",
            "Third paper about physics",
        ]
        embeddings = await service.embed_batch(texts, batch_size=2)

        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 768)

    @pytest.mark.asyncio
    async def test_esm2_embed(self) -> None:
        """Test ESM-2 embedding generation."""
        model_loader = get_model_loader()
        service = await model_loader.load_model("esm2")

        sequence = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEK"
        embedding = await service.embed(sequence)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (1280,)

    @pytest.mark.asyncio
    async def test_embedding_cache(self) -> None:
        """Test embedding caching."""
        model_loader = get_model_loader()
        service = await model_loader.load_model("specter2")

        text = "Test paper for caching"

        # First call - generates embedding
        embedding1 = await service.embed_with_cache(text)

        # Second call - should use cache
        embedding2 = await service.embed_with_cache(text)

        np.testing.assert_array_equal(embedding1, embedding2)

    @pytest.mark.asyncio
    async def test_invalid_input(self) -> None:
        """Test embedding with invalid input."""
        model_loader = get_model_loader()
        service = await model_loader.load_model("specter2")

        with pytest.raises(EmbeddingError):
            await service.embed(None)

    @pytest.mark.asyncio
    async def test_empty_batch(self) -> None:
        """Test embedding with empty batch."""
        model_loader = get_model_loader()
        service = await model_loader.load_model("specter2")

        with pytest.raises(EmbeddingError):
            await service.embed_batch([])
