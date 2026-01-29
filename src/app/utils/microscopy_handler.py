"""Microscopy image handling for multi-channel TIFF files."""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np
from PIL import Image

from app.core.exceptions import ImageLoadError, InvalidChannelError

logger = logging.getLogger(__name__)

# Standard channel color mappings
CHANNEL_COLOR_MAP = {
    "DAPI": (0, 0, 1),  # Blue
    "GFP": (0, 1, 0),  # Green
    "RFP": (1, 0, 0),  # Red
    "FITC": (0, 1, 0),  # Green
    "TRITC": (1, 0, 0),  # Red
    "CY5": (1, 0, 1),  # Magenta
    "BRIGHTFIELD": (1, 1, 1),  # White
}


def load_multipage_tiff(image_path: str) -> List[np.ndarray]:
    """Load all pages from a multi-page TIFF file.

    Args:
        image_path: Path to TIFF file

    Returns:
        List of numpy arrays, one per page

    Raises:
        ImageLoadError: If TIFF cannot be loaded
    """
    try:
        image = Image.open(image_path)
        frames = []

        for frame_idx in range(getattr(image, "n_frames", 1)):
            image.seek(frame_idx)
            frame_array = np.array(image)
            frames.append(frame_array)

        return frames
    except Exception as e:
        logger.error(f"Failed to load multi-page TIFF {image_path}: {e}")
        raise ImageLoadError(f"Failed to load TIFF: {str(e)}")


def normalize_channel_intensity(
    channel_array: np.ndarray, percentile_clip: float = 99.5
) -> np.ndarray:
    """Normalize channel intensity to [0, 1] with percentile clipping.

    Args:
        channel_array: Channel data array
        percentile_clip: Percentile for upper clipping

    Returns:
        Normalized array in [0, 1]
    """
    channel_float = channel_array.astype(np.float32)

    lower = np.percentile(channel_float, 0.5)
    upper = np.percentile(channel_float, percentile_clip)

    if upper > lower:
        channel_float = (channel_float - lower) / (upper - lower)
        channel_float = np.clip(channel_float, 0, 1)
    else:
        channel_float = np.zeros_like(channel_float)

    return channel_float


def create_rgb_composite(
    channels: Dict[str, np.ndarray], channel_names: List[str]
) -> np.ndarray:
    """Create RGB composite from named channels.

    Args:
        channels: Dictionary mapping channel names to arrays
        channel_names: List of channel names to use

    Returns:
        RGB composite array (H, W, 3)

    Raises:
        InvalidChannelError: If channel not found
    """
    if not channel_names:
        raise InvalidChannelError("No channels specified for composite")

    first_channel = channels[channel_names[0]]
    height, width = first_channel.shape[:2]
    rgb_composite = np.zeros((height, width, 3), dtype=np.float32)

    for channel_name in channel_names:
        if channel_name not in channels:
            raise InvalidChannelError(f"Channel not found: {channel_name}")

        channel_data = channels[channel_name]
        normalized = normalize_channel_intensity(channel_data)

        color = CHANNEL_COLOR_MAP.get(
            channel_name.upper(), (1, 1, 1)
        )

        for i in range(3):
            rgb_composite[:, :, i] += normalized * color[i]

    rgb_composite = np.clip(rgb_composite, 0, 1)

    return rgb_composite


def create_composite_from_frames(
    frames: List[np.ndarray], channel_names: List[str]
) -> np.ndarray:
    """Create RGB composite from list of frames.

    Args:
        frames: List of channel frames
        channel_names: List of channel names

    Returns:
        RGB composite array (H, W, 3)

    Raises:
        InvalidChannelError: If frame count mismatch
    """
    if len(frames) != len(channel_names):
        raise InvalidChannelError(
            f"Frame count ({len(frames)}) does not match "
            f"channel names ({len(channel_names)})"
        )

    channels = {name: frame for name, frame in zip(channel_names, frames)}
    return create_rgb_composite(channels, channel_names)


def convert_composite_to_pil(composite_array: np.ndarray) -> Image.Image:
    """Convert RGB composite array to PIL Image.

    Args:
        composite_array: RGB array (H, W, 3) with values in [0, 1]

    Returns:
        PIL Image
    """
    rgb_uint8 = (composite_array * 255).astype(np.uint8)
    return Image.fromarray(rgb_uint8, mode="RGB")


def process_microscopy_image(
    image_path: str, channel_names: List[str]
) -> Image.Image:
    """Process multi-channel microscopy image into RGB composite.

    Args:
        image_path: Path to multi-page TIFF
        channel_names: List of channel names in order

    Returns:
        RGB PIL Image composite

    Raises:
        ImageLoadError: If image cannot be loaded
        InvalidChannelError: If channels invalid
    """
    frames = load_multipage_tiff(image_path)

    if len(frames) == 1:
        normalized = normalize_channel_intensity(frames[0])
        rgb_array = np.stack([normalized] * 3, axis=-1)
    else:
        rgb_array = create_composite_from_frames(frames, channel_names)

    return convert_composite_to_pil(rgb_array)


def extract_microscopy_metadata(image_path: str) -> dict:
    """Extract metadata from microscopy image.

    Args:
        image_path: Path to image file

    Returns:
        Dictionary with microscopy metadata
    """
    try:
        image = Image.open(image_path)
        metadata = {
            "width": image.width,
            "height": image.height,
            "format": image.format,
            "n_frames": getattr(image, "n_frames", 1),
        }

        if hasattr(image, "tag_v2"):
            tiff_tags = {}
            for tag, value in image.tag_v2.items():
                try:
                    tiff_tags[str(tag)] = str(value)
                except Exception:
                    pass
            if tiff_tags:
                metadata["tiff_tags"] = tiff_tags

        return metadata
    except Exception as e:
        logger.warning(f"Failed to extract microscopy metadata: {e}")
        return {"error": str(e)}
