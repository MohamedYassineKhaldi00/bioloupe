"""High-level image embedding methods for ImageEmbeddingService."""

from __future__ import annotations

import hashlib
import logging
from typing import List

import httpx
import numpy as np
from PIL import Image

from app.core.exceptions import EmbeddingError, ImageLoadError
from app.services.embedding.image_embedding import ImageEmbeddingService
from app.utils.image_preprocessor import (
    extract_image_metadata,
    load_image_from_bytes,
    load_image_from_path,
)
from app.utils.microscopy_handler import (
    extract_microscopy_metadata,
    process_microscopy_image,
)

logger = logging.getLogger(__name__)


async def embed_image_from_path(
    service: ImageEmbeddingService,
    image_path: str,
    image_type: str = "standard",
    channels: List[str] | None = None,
) -> tuple[np.ndarray, dict]:
    """Embed image from file path.

    Args:
        service: ImageEmbeddingService instance
        image_path: Path to image file
        image_type: Type of image (standard or microscopy)
        channels: Channel names for microscopy images

    Returns:
        Tuple of (embedding, metadata)

    Raises:
        EmbeddingError: If embedding fails
        ImageLoadError: If image cannot be loaded
    """
    try:
        if image_type == "microscopy" and channels:
            image = process_microscopy_image(image_path, channels)
            metadata = extract_microscopy_metadata(image_path)
            metadata["image_type"] = "microscopy"
            metadata["channels"] = channels
        else:
            image = load_image_from_path(image_path)
            metadata = extract_image_metadata(image)
            metadata["image_type"] = "standard"

        embedding = await service.embed(image)

        metadata["embedding_dim"] = len(embedding)
        metadata["model"] = service.model_name

        return embedding, metadata

    except Exception as e:
        logger.error(f"Failed to embed image from path {image_path}: {e}")
        raise EmbeddingError(f"Image embedding failed: {str(e)}")


async def embed_image_from_url(
    service: ImageEmbeddingService,
    url: str,
    timeout: float = 30.0,
) -> tuple[np.ndarray, dict]:
    """Embed image from URL.

    Args:
        service: ImageEmbeddingService instance
        url: Image URL (e.g., presigned S3 URL)
        timeout: Request timeout in seconds

    Returns:
        Tuple of (embedding, metadata)

    Raises:
        EmbeddingError: If embedding fails
        ImageLoadError: If image cannot be downloaded
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            response.raise_for_status()

            image_bytes = response.content
            etag = response.headers.get("etag", "").strip('"')

        image = load_image_from_bytes(image_bytes)
        metadata = extract_image_metadata(image)
        metadata["source_url"] = url
        metadata["image_type"] = "standard"

        if etag:
            metadata["etag"] = etag

        embedding = await service.embed_with_cache_by_hash(
            image, compute_image_hash(image_bytes)
        )

        metadata["embedding_dim"] = len(embedding)
        metadata["model"] = service.model_name

        return embedding, metadata

    except httpx.HTTPError as e:
        logger.error(f"Failed to download image from {url}: {e}")
        raise ImageLoadError(f"Failed to download image: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to embed image from URL {url}: {e}")
        raise EmbeddingError(f"Image embedding failed: {str(e)}")


async def embed_microscopy_from_path(
    service: ImageEmbeddingService,
    image_path: str,
    channels: List[str],
    strategy: str = "composite",
) -> tuple[np.ndarray, dict]:
    """Embed microscopy image with channel handling.

    Args:
        service: ImageEmbeddingService instance
        image_path: Path to multi-channel TIFF
        channels: List of channel names
        strategy: Embedding strategy (composite or separate)

    Returns:
        Tuple of (embedding, metadata)

    Raises:
        EmbeddingError: If embedding fails
    """
    try:
        metadata = extract_microscopy_metadata(image_path)
        metadata["image_type"] = "microscopy"
        metadata["channels"] = channels
        metadata["strategy"] = strategy

        if strategy == "composite":
            composite_image = process_microscopy_image(image_path, channels)
            embedding = await service.embed(composite_image)

        elif strategy == "separate":
            from app.utils.microscopy_handler import load_multipage_tiff
            from app.utils.image_preprocessor import convert_to_rgb

            frames = load_multipage_tiff(image_path)
            embeddings = []

            for frame in frames:
                frame_image = Image.fromarray(
                    (frame * 255).astype("uint8") if frame.max() <= 1 else frame.astype("uint8")
                )
                frame_image = convert_to_rgb(frame_image)
                frame_embedding = await service.embed(frame_image)
                embeddings.append(frame_embedding)

            embedding = np.mean(embeddings, axis=0)

        else:
            raise EmbeddingError(f"Unknown strategy: {strategy}")

        metadata["embedding_dim"] = len(embedding)
        metadata["model"] = service.model_name

        return embedding, metadata

    except Exception as e:
        logger.error(f"Failed to embed microscopy image {image_path}: {e}")
        raise EmbeddingError(f"Microscopy embedding failed: {str(e)}")


def compute_image_hash(image_bytes: bytes) -> str:
    """Compute SHA256 hash of image bytes.

    Args:
        image_bytes: Image data

    Returns:
        Hex digest of hash
    """
    return hashlib.sha256(image_bytes).hexdigest()


async def embed_with_cache_by_hash(
    service: ImageEmbeddingService, image: Image.Image, image_hash: str
) -> np.ndarray:
    """Generate embedding with caching by image hash.

    Args:
        service: ImageEmbeddingService instance
        image: PIL Image
        image_hash: SHA256 hash of image bytes

    Returns:
        Embedding vector
    """
    if not service.settings.ml_enable_caching:
        return await service.embed(image)

    cache_key = f"embedding:{service.model_name}:image:{image_hash}"
    cached = await service._get_from_cache(cache_key)

    if cached is not None:
        return cached

    embedding = await service.embed(image)
    await service._save_to_cache(cache_key, embedding)
    return embedding


ImageEmbeddingService.embed_with_cache_by_hash = embed_with_cache_by_hash
