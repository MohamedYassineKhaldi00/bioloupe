"""Image preprocessing utilities for CLIP embeddings."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Tuple

import numpy as np
from PIL import Image

from app.core.exceptions import ImageLoadError, UnsupportedFormatError

logger = logging.getLogger(__name__)

# CLIP standard preprocessing constants
CLIP_IMAGE_SIZE = 224
CLIP_MEAN = np.array([0.48145466, 0.4578275, 0.40821073])
CLIP_STD = np.array([0.26862954, 0.26130258, 0.27577711])

SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}


def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    """Load PIL Image from bytes.

    Args:
        image_bytes: Image data as bytes

    Returns:
        PIL Image

    Raises:
        ImageLoadError: If image cannot be loaded
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        return image
    except Exception as e:
        logger.error(f"Failed to load image from bytes: {e}")
        raise ImageLoadError(f"Failed to load image: {str(e)}")


def load_image_from_path(image_path: str) -> Image.Image:
    """Load PIL Image from file path.

    Args:
        image_path: Path to image file

    Returns:
        PIL Image

    Raises:
        ImageLoadError: If image cannot be loaded
        UnsupportedFormatError: If format is not supported
    """
    try:
        from pathlib import Path

        path = Path(image_path)
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            raise UnsupportedFormatError(
                f"Unsupported format: {path.suffix}. "
                f"Supported: {', '.join(SUPPORTED_FORMATS)}"
            )

        image = Image.open(image_path)
        return image
    except UnsupportedFormatError:
        raise
    except Exception as e:
        logger.error(f"Failed to load image from {image_path}: {e}")
        raise ImageLoadError(f"Failed to load image: {str(e)}")


def convert_to_rgb(image: Image.Image) -> Image.Image:
    """Convert image to RGB format.

    Args:
        image: PIL Image

    Returns:
        RGB PIL Image
    """
    if image.mode == "RGB":
        return image

    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        return background

    if image.mode in ("L", "I", "F"):
        return image.convert("RGB")

    return image.convert("RGB")


def resize_image(
    image: Image.Image, target_size: int = CLIP_IMAGE_SIZE
) -> Image.Image:
    """Resize image to target size maintaining aspect ratio with center crop.

    Args:
        image: PIL Image
        target_size: Target size (width and height)

    Returns:
        Resized PIL Image
    """
    width, height = image.size

    if width < height:
        new_width = target_size
        new_height = int(height * (target_size / width))
    else:
        new_height = target_size
        new_width = int(width * (target_size / height))

    image = image.resize((new_width, new_height), Image.BICUBIC)

    left = (new_width - target_size) // 2
    top = (new_height - target_size) // 2
    right = left + target_size
    bottom = top + target_size

    return image.crop((left, top, right, bottom))


def normalize_image(
    image_array: np.ndarray,
    mean: np.ndarray = CLIP_MEAN,
    std: np.ndarray = CLIP_STD,
) -> np.ndarray:
    """Normalize image array with mean and std.

    Args:
        image_array: Image array (H, W, C) with values in [0, 1]
        mean: Mean values for each channel
        std: Standard deviation for each channel

    Returns:
        Normalized image array
    """
    return (image_array - mean) / std


def preprocess_for_clip(image: Image.Image) -> np.ndarray:
    """Preprocess image for CLIP model.

    Args:
        image: PIL Image

    Returns:
        Preprocessed image array (C, H, W)
    """
    image = convert_to_rgb(image)
    image = resize_image(image, CLIP_IMAGE_SIZE)

    image_array = np.array(image).astype(np.float32) / 255.0

    image_array = normalize_image(image_array)

    image_array = np.transpose(image_array, (2, 0, 1))

    return image_array


def extract_image_metadata(image: Image.Image) -> dict:
    """Extract metadata from image.

    Args:
        image: PIL Image

    Returns:
        Dictionary with image metadata
    """
    metadata = {
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "format": image.format,
    }

    try:
        exif_data = image.getexif()
        if exif_data:
            metadata["exif"] = {k: str(v) for k, v in exif_data.items()}
    except Exception as e:
        logger.debug(f"Could not extract EXIF data: {e}")

    return metadata
