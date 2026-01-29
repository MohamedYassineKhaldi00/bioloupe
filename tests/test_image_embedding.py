"""Tests for image embedding service."""

import pytest
import numpy as np
from PIL import Image
from unittest.mock import Mock, patch, AsyncMock

from app.core.ml_config import IMAGE_EMBEDDING_CONFIG
from app.services.embedding.image_embedding import ImageEmbeddingService
from app.core.exceptions import (
    ImageLoadError,
    UnsupportedFormatError,
    InvalidChannelError,
    EmbeddingError,
)


@pytest.fixture
def service():
    """Create ImageEmbeddingService instance."""
    return ImageEmbeddingService(IMAGE_EMBEDDING_CONFIG)


@pytest.fixture
def sample_image():
    """Create sample RGB image."""
    return Image.new("RGB", (224, 224), color="red")


@pytest.fixture
def sample_grayscale_image():
    """Create sample grayscale image."""
    return Image.new("L", (224, 224), color=128)


@pytest.fixture
def sample_rgba_image():
    """Create sample RGBA image."""
    return Image.new("RGBA", (224, 224), color=(255, 0, 0, 200))


class TestImagePreprocessing:
    """Test image preprocessing utilities."""

    def test_convert_rgb_to_rgb(self, sample_image):
        """Test RGB image remains unchanged."""
        from app.utils.image_preprocessor import convert_to_rgb

        result = convert_to_rgb(sample_image)
        assert result.mode == "RGB"
        assert result.size == sample_image.size

    def test_convert_grayscale_to_rgb(self, sample_grayscale_image):
        """Test grayscale to RGB conversion."""
        from app.utils.image_preprocessor import convert_to_rgb

        result = convert_to_rgb(sample_grayscale_image)
        assert result.mode == "RGB"
        assert result.size == sample_grayscale_image.size

    def test_convert_rgba_to_rgb(self, sample_rgba_image):
        """Test RGBA to RGB conversion with white background."""
        from app.utils.image_preprocessor import convert_to_rgb

        result = convert_to_rgb(sample_rgba_image)
        assert result.mode == "RGB"
        assert result.size == sample_rgba_image.size

    def test_resize_image(self, sample_image):
        """Test image resizing with center crop."""
        from app.utils.image_preprocessor import resize_image

        large_image = Image.new("RGB", (800, 600), color="blue")
        result = resize_image(large_image, target_size=224)

        assert result.size == (224, 224)

    def test_normalize_image(self):
        """Test image normalization."""
        from app.utils.image_preprocessor import normalize_image, CLIP_MEAN, CLIP_STD

        image_array = np.ones((224, 224, 3), dtype=np.float32) * 0.5
        result = normalize_image(image_array, CLIP_MEAN, CLIP_STD)

        assert result.shape == (224, 224, 3)
        assert result.dtype == np.float32

    def test_preprocess_for_clip(self, sample_image):
        """Test complete CLIP preprocessing pipeline."""
        from app.utils.image_preprocessor import preprocess_for_clip

        result = preprocess_for_clip(sample_image)

        assert result.shape == (3, 224, 224)
        assert result.dtype == np.float32

    def test_extract_image_metadata(self, sample_image):
        """Test metadata extraction."""
        from app.utils.image_preprocessor import extract_image_metadata

        metadata = extract_image_metadata(sample_image)

        assert metadata["width"] == 224
        assert metadata["height"] == 224
        assert metadata["mode"] == "RGB"


class TestMicroscopyHandler:
    """Test microscopy image handling."""

    def test_normalize_channel_intensity(self):
        """Test channel intensity normalization."""
        from app.utils.microscopy_handler import normalize_channel_intensity

        channel = np.random.randint(0, 4096, (512, 512), dtype=np.uint16)
        result = normalize_channel_intensity(channel)

        assert result.shape == channel.shape
        assert result.dtype == np.float32
        assert result.min() >= 0
        assert result.max() <= 1

    def test_create_rgb_composite(self):
        """Test RGB composite creation from channels."""
        from app.utils.microscopy_handler import create_rgb_composite

        channels = {
            "DAPI": np.random.rand(512, 512).astype(np.float32),
            "GFP": np.random.rand(512, 512).astype(np.float32),
            "RFP": np.random.rand(512, 512).astype(np.float32),
        }

        result = create_rgb_composite(channels, ["DAPI", "GFP", "RFP"])

        assert result.shape == (512, 512, 3)
        assert result.dtype == np.float32
        assert result.min() >= 0
        assert result.max() <= 1

    def test_create_composite_invalid_channel(self):
        """Test error handling for invalid channel."""
        from app.utils.microscopy_handler import create_rgb_composite

        channels = {"DAPI": np.random.rand(512, 512).astype(np.float32)}

        with pytest.raises(InvalidChannelError):
            create_rgb_composite(channels, ["DAPI", "INVALID"])


class TestImageEmbeddingService:
    """Test ImageEmbeddingService."""

    @pytest.mark.asyncio
    async def test_load_model(self, service):
        """Test model loading."""
        with patch.object(service, "_load_model_sync") as mock_load:
            mock_model = Mock()
            mock_processor = Mock()
            mock_load.return_value = (mock_model, mock_processor)

            await service.load_model()

            assert service.is_loaded
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_without_loading(self, service, sample_image):
        """Test embedding triggers model loading."""
        with patch.object(service, "load_model", new=AsyncMock()) as mock_load:
            with patch.object(service, "_embed_sync") as mock_embed:
                mock_embed.return_value = np.random.rand(512).astype(np.float32)

                await service.embed(sample_image)

                mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_batch(self, service, sample_image):
        """Test batch embedding."""
        images = [sample_image] * 5

        with patch.object(service, "load_model", new=AsyncMock()):
            with patch.object(service, "_embed_batch_sync") as mock_batch:
                mock_batch.return_value = np.random.rand(5, 512).astype(np.float32)
                service._is_loaded = True

                embeddings = await service.embed_batch(images, batch_size=2)

                assert embeddings.shape == (5, 512)
                mock_batch.assert_called_once()


class TestImageEmbeddingMethods:
    """Test high-level embedding methods."""

    @pytest.mark.asyncio
    async def test_embed_image_from_path(self, service):
        """Test embedding from file path."""
        from app.services.embedding.image_embedding_methods import embed_image_from_path

        with patch("app.utils.image_preprocessor.load_image_from_path") as mock_load:
            mock_load.return_value = Image.new("RGB", (224, 224))

            with patch.object(service, "embed", new=AsyncMock()) as mock_embed:
                mock_embed.return_value = np.random.rand(512).astype(np.float32)

                embedding, metadata = await embed_image_from_path(
                    service, "/fake/path.jpg", image_type="standard"
                )

                assert embedding.shape == (512,)
                assert metadata["image_type"] == "standard"
                assert "embedding_dim" in metadata

    @pytest.mark.asyncio
    async def test_embed_image_from_url(self, service):
        """Test embedding from URL."""
        from app.services.embedding.image_embedding_methods import embed_image_from_url

        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.headers = {"etag": "abc123"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with patch("app.utils.image_preprocessor.load_image_from_bytes") as mock_load:
                mock_load.return_value = Image.new("RGB", (224, 224))

                with patch.object(service, "embed_with_cache_by_hash", new=AsyncMock()) as mock_embed:
                    mock_embed.return_value = np.random.rand(512).astype(np.float32)

                    embedding, metadata = await embed_image_from_url(
                        service, "https://example.com/image.jpg"
                    )

                    assert embedding.shape == (512,)
                    assert metadata["source_url"] == "https://example.com/image.jpg"
                    assert metadata["etag"] == "abc123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
