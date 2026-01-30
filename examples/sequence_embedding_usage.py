"""Example usage of sequence embedding service."""

import asyncio
from pathlib import Path

from app.core.ml_config import SEQUENCE_EMBEDDING_CONFIG
from app.services.embedding.sequence_embedding import SequenceEmbeddingService


async def embed_protein_example() -> None:
    """Example: Embed a protein sequence."""
    service = SequenceEmbeddingService(SEQUENCE_EMBEDDING_CONFIG)
    await service.load_model()

    # Example protein sequence (human insulin)
    protein_seq = (
        "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"
    )

    embedding = await service.embed_sequence(protein_seq, sequence_type="protein")
    print(f"Protein embedding shape: {embedding.shape}")
    print(f"First 5 dimensions: {embedding[:5]}")


async def embed_dna_example() -> None:
    """Example: Embed a DNA sequence (will be translated to protein)."""
    service = SequenceEmbeddingService(SEQUENCE_EMBEDDING_CONFIG)
    await service.load_model()

    # Example DNA sequence (ATG start codon + coding sequence)
    dna_seq = "ATGGCCCTGTGGATGCGCCTCCTGCCCCTGCTGGCGCTGCTGGCCCTCTGGGGACCTGACCCAGCCGCAGCC"

    embedding = await service.embed_sequence(dna_seq, sequence_type="dna")
    print(f"DNA (translated) embedding shape: {embedding.shape}")


async def embed_fasta_example() -> None:
    """Example: Embed sequences from FASTA file."""
    service = SequenceEmbeddingService(SEQUENCE_EMBEDDING_CONFIG)
    await service.load_model()

    # Create example FASTA file
    fasta_content = """>seq1 Human insulin chain A
GIVEQCCTSICSLYQLENYCN
>seq2 Human insulin chain B
FVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKR
"""

    fasta_path = Path("/tmp/example_sequences.fasta")
    fasta_path.write_text(fasta_content)

    embeddings = await service.embed_from_fasta(str(fasta_path))

    for seq_id, embedding in embeddings.items():
        print(f"{seq_id}: {embedding.shape}")


async def embed_long_sequence_example() -> None:
    """Example: Embed long sequence with automatic splitting."""
    service = SequenceEmbeddingService(SEQUENCE_EMBEDDING_CONFIG)
    await service.load_model()

    # Create a long sequence (2000 residues)
    long_seq = "ACDEFGHIKLMNPQRSTVWY" * 100

    embedding = await service.embed_sequence(long_seq, sequence_type="protein")
    print(f"Long sequence (2000 residues) embedding: {embedding.shape}")
    print("Automatically split into windows and averaged")


async def main() -> None:
    """Run all examples."""
    print("=== Protein Sequence Embedding ===")
    await embed_protein_example()

    print("\n=== DNA Sequence Embedding ===")
    await embed_dna_example()

    print("\n=== FASTA File Embedding ===")
    await embed_fasta_example()

    print("\n=== Long Sequence Embedding ===")
    await embed_long_sequence_example()


if __name__ == "__main__":
    asyncio.run(main())
