"""
Example usage of the Unified Embedding Service.

This demonstrates how to integrate the unified embedding service
into material upload, update, and search workflows.
"""

import asyncio
import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.material import Material, MaterialType
from app.services.embedding import (
    EmbeddingFusion,
    EmbeddingStorageService,
    UnifiedEmbeddingService,
)


# ============================================================================
# Example 1: Material Upload with Embedding Generation
# ============================================================================


async def example_material_upload(
    session_id: uuid.UUID,
    title: str,
    abstract: str,
    db: AsyncSession,
) -> Material:
    """Upload a paper and generate its embedding.

    Args:
        session_id: Session UUID
        title: Paper title
        abstract: Paper abstract
        db: Database session

    Returns:
        Material with embedded vector stored in Qdrant
    """
    # Step 1: Create material
    material = Material(
        session_id=session_id,
        material_type=MaterialType.paper,
        title=title,
        metadata_={"abstract": abstract},
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)

    # Step 2: Generate and store embedding
    unified_service = UnifiedEmbeddingService()
    point_id = await unified_service.embed_and_upsert(material)

    # Step 3: Update material with Qdrant point ID
    material.qdrant_point_id = point_id
    await db.commit()

    print(f"✓ Material {material.id} embedded and stored at point {point_id}")
    return material


# ============================================================================
# Example 2: Batch Material Upload
# ============================================================================


async def example_batch_upload(
    materials_data: List[dict],
    db: AsyncSession,
) -> List[Material]:
    """Upload multiple materials and batch generate embeddings.

    Args:
        materials_data: List of material dicts with type, title, metadata
        db: Database session

    Returns:
        List of materials with embeddings
    """
    # Step 1: Create all materials
    materials = []
    for data in materials_data:
        material = Material(
            session_id=data["session_id"],
            material_type=data["material_type"],
            title=data["title"],
            metadata_=data.get("metadata_", {}),
        )
        materials.append(material)
        db.add(material)

    await db.commit()

    # Step 2: Batch generate embeddings
    unified_service = UnifiedEmbeddingService()
    embeddings = await unified_service.embed_batch(materials)

    # Step 3: Batch upsert to Qdrant
    storage = EmbeddingStorageService()
    point_ids = await storage.batch_upsert(materials, embeddings)

    # Step 4: Update all materials with point IDs
    for material in materials:
        mat_id = str(material.id)
        if mat_id in point_ids:
            material.qdrant_point_id = point_ids[mat_id]

    await db.commit()

    print(f"✓ Batch uploaded {len(materials)} materials")
    return materials


# ============================================================================
# Example 3: Material Update with Re-embedding
# ============================================================================


async def example_material_update(
    material_id: uuid.UUID,
    new_title: str,
    new_abstract: str,
    db: AsyncSession,
) -> Material:
    """Update a material and regenerate its embedding.

    Args:
        material_id: Material UUID
        new_title: Updated title
        new_abstract: Updated abstract
        db: Database session

    Returns:
        Updated material with new embedding
    """
    # Step 1: Fetch material
    result = await db.execute(select(Material).where(Material.id == material_id))
    material = result.scalar_one()

    # Step 2: Update material
    material.title = new_title
    material.metadata_["abstract"] = new_abstract
    await db.commit()

    # Step 3: Invalidate cache
    unified_service = UnifiedEmbeddingService()
    await unified_service.invalidate_cache(material_id)

    # Step 4: Regenerate embedding
    point_id = await unified_service.embed_and_upsert(material)
    material.qdrant_point_id = point_id
    await db.commit()

    print(f"✓ Material {material_id} updated and re-embedded")
    return material


# ============================================================================
# Example 4: Semantic Search
# ============================================================================


async def example_semantic_search(
    query_text: str,
    session_id: uuid.UUID,
    limit: int = 20,
) -> List[Material]:
    """Search for materials semantically similar to query.

    Args:
        query_text: Search query
        session_id: Filter by session
        limit: Number of results

    Returns:
        List of similar materials
    """
    # Step 1: Generate query embedding
    query_material = Material(
        session_id=session_id,
        material_type=MaterialType.paper,
        title=query_text,
        metadata_={"abstract": query_text},
    )

    unified_service = UnifiedEmbeddingService()
    query_embedding = await unified_service.embed_material(query_material)

    # Step 2: Search Qdrant
    storage = EmbeddingStorageService()
    results = await storage.search_similar(
        query_embedding=query_embedding,
        limit=limit,
        filters={"session_id": str(session_id)},
    )

    # Step 3: Extract material IDs and scores
    print(f"✓ Found {len(results)} similar materials:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result.payload['title']} (score: {result.score:.3f})")

    return results


# ============================================================================
# Example 5: Multi-Modal Fusion (Future Enhancement)
# ============================================================================


async def example_multimodal_fusion(
    paper_material: Material,
    image_material: Material,
) -> None:
    """Fuse text and image embeddings for a paper with figures.

    Args:
        paper_material: Paper material
        image_material: Image material (figure from paper)
    """
    # Step 1: Generate individual embeddings
    unified_service = UnifiedEmbeddingService()

    paper_embedding = await unified_service.embed_material(paper_material)
    image_embedding = await unified_service.embed_material(image_material)

    # Step 2: Fuse embeddings
    fusion = EmbeddingFusion()

    # Option A: Concatenate (preserves all information)
    fused_concat = fusion.fuse(
        embeddings={"text": paper_embedding, "image": image_embedding},
        method="concat",
    )
    print(f"✓ Concatenated embedding: {fused_concat.shape}")

    # Option B: Weighted average (requires same dimensions)
    # Note: SPECTER2 (768) != CLIP (512), so use concat or project first

    # Option C: Custom weights for future use
    custom_weights = {"text": 0.7, "image": 0.3}
    # fused_weighted = fusion.fuse(
    #     embeddings={"text": paper_embedding, "image": image_embedding},
    #     method="weighted_average",
    #     weights=custom_weights,
    # )


# ============================================================================
# Example 6: Cache Management
# ============================================================================


async def example_cache_management(material_id: uuid.UUID) -> None:
    """Demonstrate cache usage patterns.

    Args:
        material_id: Material UUID
    """
    unified_service = UnifiedEmbeddingService()

    # Check cache
    cached_embedding = await unified_service._get_cached_embedding(material_id)

    if cached_embedding is not None:
        print(f"✓ Cache hit for {material_id}")
        print(f"  Embedding shape: {cached_embedding.shape}")
    else:
        print(f"✗ Cache miss for {material_id}")

    # Invalidate cache (e.g., after material update)
    await unified_service.invalidate_cache(material_id)
    print(f"✓ Cache invalidated for {material_id}")


# ============================================================================
# Example 7: Sequence Embedding
# ============================================================================


async def example_sequence_embedding(
    session_id: uuid.UUID,
    sequence: str,
    sequence_type: str = "protein",
    db: AsyncSession,
) -> Material:
    """Upload a sequence and generate its embedding.

    Args:
        session_id: Session UUID
        sequence: Amino acid or nucleotide sequence
        sequence_type: Type (protein, dna, rna)
        db: Database session

    Returns:
        Material with sequence embedding
    """
    # Step 1: Create sequence material
    material = Material(
        session_id=session_id,
        material_type=MaterialType.sequence,
        title=f"Sequence ({len(sequence)} residues)",
        metadata_={
            "sequence": sequence,
            "sequence_type": sequence_type,
        },
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)

    # Step 2: Generate embedding (ESM-2)
    unified_service = UnifiedEmbeddingService()
    point_id = await unified_service.embed_and_upsert(material)

    # Step 3: Update material
    material.qdrant_point_id = point_id
    await db.commit()

    print(f"✓ Sequence embedded with ESM-2 (1280-dim)")
    return material


# ============================================================================
# Example 8: Image Embedding
# ============================================================================


async def example_image_embedding(
    session_id: uuid.UUID,
    image_path: str,
    db: AsyncSession,
) -> Material:
    """Upload an image and generate its embedding.

    Args:
        session_id: Session UUID
        image_path: Path to image file
        db: Database session

    Returns:
        Material with image embedding
    """
    # Step 1: Create image material
    material = Material(
        session_id=session_id,
        material_type=MaterialType.image,
        title="Microscopy Image",
        file_url=image_path,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)

    # Step 2: Generate embedding (CLIP)
    unified_service = UnifiedEmbeddingService()
    point_id = await unified_service.embed_and_upsert(material)

    # Step 3: Update material
    material.qdrant_point_id = point_id
    await db.commit()

    print(f"✓ Image embedded with CLIP (512-dim)")
    return material


# ============================================================================
# Example 9: Error Handling
# ============================================================================


async def example_error_handling(material: Material) -> None:
    """Demonstrate proper error handling.

    Args:
        material: Material to embed
    """
    from app.core.exceptions import EmbeddingError

    unified_service = UnifiedEmbeddingService()

    try:
        embedding = await unified_service.embed_material(material)
        print(f"✓ Successfully embedded material {material.id}")

    except EmbeddingError as e:
        # Handle embedding-specific errors
        print(f"✗ Embedding failed: {e}")
        # Log error, notify user, retry, etc.

    except Exception as e:
        # Handle unexpected errors
        print(f"✗ Unexpected error: {e}")
        # Log for investigation


# ============================================================================
# Example 10: Complete Workflow
# ============================================================================


async def example_complete_workflow():
    """Demonstrate complete material lifecycle with embeddings."""
    session_id = uuid.uuid4()

    async for db in get_db():
        # 1. Upload materials
        print("\n1. Uploading materials...")
        paper = await example_material_upload(
            session_id=session_id,
            title="CRISPR-Cas9 Gene Editing",
            abstract="This paper describes...",
            db=db,
        )

        # 2. Update material
        print("\n2. Updating material...")
        paper = await example_material_update(
            material_id=paper.id,
            new_title="CRISPR-Cas9 Gene Editing (Revised)",
            new_abstract="This paper describes... [updated]",
            db=db,
        )

        # 3. Search for similar materials
        print("\n3. Searching for similar materials...")
        results = await example_semantic_search(
            query_text="CRISPR gene editing",
            session_id=session_id,
            limit=5,
        )

        # 4. Check cache
        print("\n4. Checking cache...")
        await example_cache_management(paper.id)

        print("\n✓ Complete workflow finished")
        break


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Run complete workflow example
    asyncio.run(example_complete_workflow())
