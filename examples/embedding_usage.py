"""Example usage of the embedding infrastructure."""

from __future__ import annotations

import asyncio
import logging

from app.services.embedding import get_model_loader
from app.utils.device_manager import get_device_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_device_detection() -> None:
    """Example: Detect available devices."""
    logger.info("=== Device Detection ===")

    device_manager = get_device_manager()

    # Check CUDA availability
    if device_manager.is_cuda_available():
        logger.info(f"CUDA available: {device_manager.get_cuda_device_count()} devices")

        # Get GPU memory info
        memory_info = device_manager.get_device_memory_info("cuda:0")
        logger.info(
            f"GPU memory - Total: {memory_info['total'] / 1e9:.2f} GB, "
            f"Available: {memory_info['available'] / 1e9:.2f} GB"
        )
    else:
        logger.info("CUDA not available, using CPU")

    # Select device
    device = device_manager.select_device("auto")
    logger.info(f"Selected device: {device}")


async def example_load_model() -> None:
    """Example: Load and use a single model."""
    logger.info("\n=== Load SPECTER2 Model ===")

    model_loader = get_model_loader()

    # Load SPECTER2 for paper embeddings
    service = await model_loader.load_model("specter2")
    logger.info(f"Model loaded: {service.model_name}")
    logger.info(f"Embedding dimension: {await service.get_embedding_dim()}")

    # Generate single embedding
    paper_text = (
        "Deep learning for protein structure prediction. "
        "We present AlphaFold, a novel approach using attention mechanisms."
    )
    embedding = await service.embed(paper_text)
    logger.info(f"Generated embedding shape: {embedding.shape}")


async def example_batch_embedding() -> None:
    """Example: Generate batch embeddings."""
    logger.info("\n=== Batch Embedding ===")

    model_loader = get_model_loader()
    service = await model_loader.load_model("specter2")

    # Prepare batch of papers
    papers = [
        "Machine learning for genomics and precision medicine",
        "CRISPR gene editing: applications and challenges",
        "Single-cell RNA sequencing reveals cellular heterogeneity",
        "Protein folding prediction using deep neural networks",
        "Microbiome analysis using metagenomic sequencing",
    ]

    # Generate embeddings in batches
    embeddings = await service.embed_batch(papers, batch_size=2)
    logger.info(f"Generated {len(embeddings)} embeddings, shape: {embeddings.shape}")


async def example_with_caching() -> None:
    """Example: Use embedding caching."""
    logger.info("\n=== Embedding with Caching ===")

    model_loader = get_model_loader()
    service = await model_loader.load_model("specter2")

    text = "Computational methods for drug discovery"

    # First call - generates embedding
    logger.info("First call (generates embedding)...")
    embedding1 = await service.embed_with_cache(text)

    # Second call - retrieves from cache
    logger.info("Second call (from cache)...")
    embedding2 = await service.embed_with_cache(text)

    logger.info(f"Embeddings match: {(embedding1 == embedding2).all()}")


async def example_multiple_models() -> None:
    """Example: Load and use multiple models."""
    logger.info("\n=== Multiple Models ===")

    model_loader = get_model_loader()

    # Load paper embedding model
    specter2 = await model_loader.load_model("specter2")
    logger.info(f"Loaded {specter2.model_name}")

    # Load protein sequence model
    esm2 = await model_loader.load_model("esm2")
    logger.info(f"Loaded {esm2.model_name}")

    # Check loaded models
    loaded = model_loader.get_loaded_models()
    logger.info(f"Currently loaded models: {loaded}")

    # Embed paper
    paper_embedding = await specter2.embed(
        "Protein engineering using machine learning"
    )
    logger.info(f"Paper embedding shape: {paper_embedding.shape}")

    # Embed protein sequence
    sequence = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEK"
    protein_embedding = await esm2.embed(sequence)
    logger.info(f"Protein embedding shape: {protein_embedding.shape}")


async def example_model_management() -> None:
    """Example: Manage model lifecycle."""
    logger.info("\n=== Model Management ===")

    model_loader = get_model_loader()

    # Load model
    await model_loader.load_model("specter2")
    logger.info(f"Loaded models: {model_loader.get_loaded_models()}")

    # Check if specific model is loaded
    is_loaded = model_loader.is_model_loaded("specter2")
    logger.info(f"SPECTER2 loaded: {is_loaded}")

    # Unload model to free memory
    await model_loader.unload_model("specter2")
    logger.info(f"After unload: {model_loader.get_loaded_models()}")

    # Load again (lazy loading)
    service = await model_loader.load_model("specter2")
    logger.info(f"Reloaded: {service.model_name}")


async def example_error_handling() -> None:
    """Example: Handle errors."""
    logger.info("\n=== Error Handling ===")

    from app.core.exceptions import EmbeddingError, ModelLoadError

    model_loader = get_model_loader()

    try:
        service = await model_loader.load_model("specter2")

        # Try with invalid input
        await service.embed(None)

    except EmbeddingError as e:
        logger.info(f"Caught EmbeddingError: {e.message}")

    except ModelLoadError as e:
        logger.info(f"Caught ModelLoadError: {e.message}")


async def main() -> None:
    """Run all examples."""
    logger.info("Starting Embedding Infrastructure Examples\n")

    try:
        await example_device_detection()
        await example_load_model()
        await example_batch_embedding()
        await example_with_caching()
        await example_multiple_models()
        await example_model_management()
        await example_error_handling()

    except Exception as e:
        logger.error(f"Example failed: {e}")
        logger.info(
            "\nNote: These examples require ML dependencies installed:\n"
            "  pip install torch transformers numpy pillow psutil"
        )

    logger.info("\n=== Examples Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
