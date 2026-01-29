"""Example usage of Paper Embedding Service (E5-S2).

This example demonstrates how to use the PaperEmbeddingService to:
1. Generate embeddings from paper metadata (title + abstract)
2. Generate embeddings from PDF files
3. Batch process multiple papers
4. Use with Material model and DOI caching
"""

import asyncio
from pathlib import Path

from app.core.ml_config import PAPER_EMBEDDING_CONFIG
from app.models.material import Material, MaterialType
from app.services.embedding.paper_embedding import PaperEmbeddingService


async def example_basic_paper_embedding() -> None:
    """Example: Embed paper from title and abstract."""
    print("\n=== Basic Paper Embedding ===")

    service = PaperEmbeddingService(PAPER_EMBEDDING_CONFIG)
    await service.load_model()

    title = "BERT: Pre-training of Deep Bidirectional Transformers"
    abstract = (
        "We introduce BERT, a new language representation model. "
        "BERT is designed to pre-train deep bidirectional "
        "representations from unlabeled text by jointly conditioning "
        "on both left and right context in all layers."
    )

    embedding = await service.embed_paper(title=title, abstract=abstract)

    print(f"Generated embedding shape: {embedding.shape}")
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")


async def example_pdf_embedding() -> None:
    """Example: Embed paper from PDF file."""
    print("\n=== PDF Paper Embedding ===")

    service = PaperEmbeddingService(PAPER_EMBEDDING_CONFIG)
    await service.load_model()

    pdf_path = "path/to/paper.pdf"

    # Check if file exists
    if not Path(pdf_path).exists():
        print(f"PDF not found: {pdf_path}")
        print("Skipping PDF embedding example...")
        return

    try:
        embedding = await service.embed_from_pdf(pdf_path)
        print(f"Generated embedding from PDF: {embedding.shape}")
    except Exception as e:
        print(f"PDF embedding failed: {e}")


async def example_material_embedding() -> None:
    """Example: Embed paper from Material model."""
    print("\n=== Material Embedding with DOI Caching ===")

    service = PaperEmbeddingService(PAPER_EMBEDDING_CONFIG)
    await service.load_model()

    # Mock Material object
    material = Material(
        material_type=MaterialType.paper,
        title="Attention Is All You Need",
        metadata_={
            "abstract": (
                "The dominant sequence transduction models are based on "
                "complex recurrent or convolutional neural networks. "
                "We propose the Transformer, a model architecture based "
                "solely on attention mechanisms."
            ),
            "doi": "10.48550/arXiv.1706.03762",
            "authors": ["Vaswani et al."],
            "year": 2017,
        },
    )

    # First embedding (will be cached by DOI)
    embedding1 = await service.embed_from_metadata(material)
    print(f"First embedding: {embedding1.shape}")

    # Second embedding (should retrieve from cache)
    embedding2 = await service.embed_from_metadata(material)
    print(f"Second embedding (from cache): {embedding2.shape}")
    print(f"Embeddings are identical: {(embedding1 == embedding2).all()}")


async def example_batch_embedding() -> None:
    """Example: Batch embed multiple papers."""
    print("\n=== Batch Paper Embedding ===")

    service = PaperEmbeddingService(PAPER_EMBEDDING_CONFIG)
    await service.load_model()

    papers = [
        (
            "BERT: Pre-training of Deep Bidirectional Transformers",
            "We introduce BERT, a new language representation model.",
            None,
        ),
        (
            "Attention Is All You Need",
            "The dominant sequence transduction models are based on RNNs.",
            None,
        ),
        (
            "GPT-3: Language Models are Few-Shot Learners",
            "We demonstrate that scaling up language models greatly improves task-agnostic performance.",
            None,
        ),
    ]

    embeddings = await service.embed_papers_batch(
        papers, batch_size=16
    )

    print(f"Generated {len(embeddings)} embeddings")
    print(f"Embedding shape: {embeddings.shape}")


async def example_full_text_embedding() -> None:
    """Example: Embed paper with full text."""
    print("\n=== Paper Embedding with Full Text ===")

    service = PaperEmbeddingService(PAPER_EMBEDDING_CONFIG)
    await service.load_model()

    title = "SPECTER: Document-level Representation Learning"
    abstract = (
        "We present SPECTER, a new method to generate document-level "
        "embeddings of scientific papers."
    )
    full_text = (
        "Introduction: Representation learning for scientific papers "
        "is important for many applications. In this work, we propose "
        "SPECTER, which uses a Transformer architecture to learn "
        "embeddings from paper titles and abstracts."
    )

    embedding = await service.embed_paper(
        title=title, abstract=abstract, full_text=full_text
    )

    print(f"Generated embedding with full text: {embedding.shape}")


async def example_error_handling() -> None:
    """Example: Error handling for invalid inputs."""
    print("\n=== Error Handling ===")

    service = PaperEmbeddingService(PAPER_EMBEDDING_CONFIG)
    await service.load_model()

    # Test empty title
    try:
        await service.embed_paper(title="", abstract="Some abstract")
    except Exception as e:
        print(f"Empty title error: {e}")

    # Test empty abstract
    try:
        await service.embed_paper(
            title="Some title", abstract=""
        )
    except Exception as e:
        print(f"Empty abstract error: {e}")

    # Test invalid PDF path
    try:
        await service.embed_from_pdf("nonexistent.pdf")
    except Exception as e:
        print(f"Invalid PDF error: {e}")


async def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("Paper Embedding Service Examples (Story E5-S2)")
    print("=" * 60)

    await example_basic_paper_embedding()
    await example_material_embedding()
    await example_batch_embedding()
    await example_full_text_embedding()
    await example_pdf_embedding()
    await example_error_handling()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
