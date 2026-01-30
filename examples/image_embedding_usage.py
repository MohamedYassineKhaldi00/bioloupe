"""Example usage of image embedding service."""

import asyncio
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.ml_config import IMAGE_EMBEDDING_CONFIG
from app.services.embedding.image_embedding import ImageEmbeddingService
from app.services.embedding.image_embedding_methods import (
    embed_image_from_path,
    embed_image_from_url,
    embed_microscopy_from_path,
)


async def example_basic_embedding():
    """Basic image embedding example."""
    print("\n=== Basic Image Embedding ===")

    service = ImageEmbeddingService(IMAGE_EMBEDDING_CONFIG)
    await service.load_model()

    image = Image.open("examples/sample_image.png")
    embedding = await service.embed(image)

    print(f"Input image: {image.size}")
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding norm: {np.linalg.norm(embedding):.4f}")


async def example_batch_embedding():
    """Batch embedding example."""
    print("\n=== Batch Embedding ===")

    service = ImageEmbeddingService(IMAGE_EMBEDDING_CONFIG)
    await service.load_model()

    image_dir = Path("examples/images")
    images = [Image.open(p) for p in image_dir.glob("*.png")[:5]]

    embeddings = await service.embed_batch(images, batch_size=2)

    print(f"Number of images: {len(images)}")
    print(f"Batch embeddings shape: {embeddings.shape}")
    print(f"Mean embedding norm: {np.linalg.norm(embeddings, axis=1).mean():.4f}")


async def example_from_path():
    """Embed image from file path."""
    print("\n=== Embedding from Path ===")

    service = ImageEmbeddingService(IMAGE_EMBEDDING_CONFIG)
    await service.load_model()

    embedding, metadata = await embed_image_from_path(
        service,
        "examples/experiment_plot.png",
        image_type="standard"
    )

    print(f"Embedding dimension: {metadata['embedding_dim']}")
    print(f"Image size: {metadata['width']}x{metadata['height']}")
    print(f"Format: {metadata['format']}")
    print(f"Model: {metadata['model']}")


async def example_from_url():
    """Embed image from URL."""
    print("\n=== Embedding from URL ===")

    service = ImageEmbeddingService(IMAGE_EMBEDDING_CONFIG)
    await service.load_model()

    url = "https://example.com/images/sample.jpg"

    try:
        embedding, metadata = await embed_image_from_url(service, url)

        print(f"Source URL: {metadata['source_url']}")
        print(f"Embedding dimension: {metadata['embedding_dim']}")
        print(f"Image size: {metadata['width']}x{metadata['height']}")

    except Exception as e:
        print(f"Failed to download from URL: {e}")


async def example_microscopy_composite():
    """Embed microscopy image with composite strategy."""
    print("\n=== Microscopy Embedding (Composite) ===")

    service = ImageEmbeddingService(IMAGE_EMBEDDING_CONFIG)
    await service.load_model()

    embedding, metadata = await embed_microscopy_from_path(
        service,
        "examples/microscopy_3channel.tif",
        channels=["DAPI", "GFP", "RFP"],
        strategy="composite"
    )

    print(f"Image type: {metadata['image_type']}")
    print(f"Channels: {metadata['channels']}")
    print(f"Number of frames: {metadata['n_frames']}")
    print(f"Strategy: {metadata['strategy']}")
    print(f"Embedding dimension: {metadata['embedding_dim']}")


async def example_microscopy_separate():
    """Embed microscopy image with separate channel strategy."""
    print("\n=== Microscopy Embedding (Separate Channels) ===")

    service = ImageEmbeddingService(IMAGE_EMBEDDING_CONFIG)
    await service.load_model()

    embedding, metadata = await embed_microscopy_from_path(
        service,
        "examples/microscopy_2channel.tif",
        channels=["DAPI", "GFP"],
        strategy="separate"
    )

    print(f"Channels: {metadata['channels']}")
    print(f"Strategy: {metadata['strategy']}")
    print(f"Embedding dimension: {metadata['embedding_dim']}")
    print("Note: Separate embeddings averaged")


async def example_similarity_search():
    """Example of computing similarity between images."""
    print("\n=== Image Similarity Search ===")

    service = ImageEmbeddingService(IMAGE_EMBEDDING_CONFIG)
    await service.load_model()

    query_image = Image.open("examples/query_image.png")
    query_embedding = await service.embed(query_image)

    database_images = [
        Image.open(f"examples/db_image_{i}.png") for i in range(5)
    ]
    db_embeddings = await service.embed_batch(database_images)

    query_norm = query_embedding / np.linalg.norm(query_embedding)
    db_norms = db_embeddings / np.linalg.norm(db_embeddings, axis=1, keepdims=True)

    similarities = np.dot(db_norms, query_norm)

    print("Cosine similarities:")
    for i, sim in enumerate(similarities):
        print(f"  Image {i}: {sim:.4f}")

    best_match = np.argmax(similarities)
    print(f"\nBest match: Image {best_match} (similarity: {similarities[best_match]:.4f})")


async def main():
    """Run all examples."""
    examples = [
        example_basic_embedding,
        example_batch_embedding,
        example_from_path,
        example_from_url,
        example_microscopy_composite,
        example_microscopy_separate,
        example_similarity_search,
    ]

    for example in examples:
        try:
            await example()
        except FileNotFoundError:
            print(f"Skipping {example.__name__}: sample files not found")
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
