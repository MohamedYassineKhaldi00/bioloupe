"""Sequence embedding service using ESM-2 model."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import numpy as np

from app.core.exceptions import EmbeddingError
from app.core.ml_config import ESM2_CONFIG, ModelConfig
from app.core.sequence_exceptions import SequenceTooLongError
from app.models.material import Material
from app.services.embedding.esm2_service import ESM2Service
from app.utils.sequence_parser import FastaParser, SequenceRecord
from app.utils.sequence_validator import (
    MAX_RESIDUES_ESM2,
    SequenceType,
    translate_dna_to_protein,
    translate_rna_to_protein,
    validate_dna,
    validate_protein,
    validate_rna,
)

logger = logging.getLogger(__name__)


class SequenceEmbeddingService(ESM2Service):
    """ESM-2 based service for sequence embeddings."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        """Initialize sequence embedding service.

        Args:
            config: Model configuration (defaults to ESM2_CONFIG)
        """
        super().__init__(config or ESM2_CONFIG)
        self._fasta_parser: FastaParser | None = None

    async def load_model(self) -> None:
        """Load model and initialize parsers."""
        await super().load_model()
        self._fasta_parser = FastaParser()

    async def embed_sequence(
        self,
        sequence: str,
        sequence_type: SequenceType = "protein",
    ) -> np.ndarray:
        """Generate embedding for a sequence.

        Args:
            sequence: Sequence string
            sequence_type: Type of sequence (protein, dna, rna)

        Returns:
            Embedding vector (1280-dim)

        Raises:
            InvalidSequenceError: If sequence invalid
            SequenceTooLongError: If sequence too long
            EmbeddingError: If embedding fails
        """
        if not self._is_loaded:
            await self.load_model()

        try:
            protein_seq = self._prepare_sequence(sequence, sequence_type)
            embedding = await self._embed_with_splitting(protein_seq)
            return embedding

        except (ValueError, TypeError) as e:
            logger.error(f"Sequence preparation failed: {e}")
            raise EmbeddingError(f"Failed to prepare sequence: {str(e)}")

    async def embed_from_fasta(self, fasta_path: str) -> dict[str, np.ndarray]:
        """Generate embeddings from FASTA file.

        Args:
            fasta_path: Path to FASTA file

        Returns:
            Dictionary mapping sequence IDs to embeddings

        Raises:
            SequenceParsingError: If parsing fails
            EmbeddingError: If embedding fails
        """
        if not self._is_loaded:
            await self.load_model()

        if self._fasta_parser is None:
            self._fasta_parser = FastaParser()

        records = self._fasta_parser.parse_file(fasta_path)
        return await self._embed_records(records)

    async def embed_from_material(self, material: Material) -> np.ndarray:
        """Generate embedding from material.

        Args:
            material: Material with sequence metadata

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If material invalid or embedding fails
        """
        if not material.metadata_:
            raise EmbeddingError("Material has no metadata")

        sequence = material.metadata_.get("sequence")
        if not sequence:
            raise EmbeddingError("Material metadata missing 'sequence' field")

        sequence_type = material.metadata_.get("sequence_type", "protein")
        return await self.embed_sequence(sequence, sequence_type)  # type: ignore

    def _prepare_sequence(
        self, sequence: str, sequence_type: SequenceType
    ) -> str:
        """Validate and convert sequence to protein.

        Args:
            sequence: Raw sequence
            sequence_type: Type of sequence

        Returns:
            Protein sequence

        Raises:
            InvalidSequenceError: If validation fails
        """
        if sequence_type == "protein":
            return validate_protein(sequence)
        elif sequence_type == "dna":
            dna_seq = validate_dna(sequence)
            return translate_dna_to_protein(dna_seq)
        elif sequence_type == "rna":
            rna_seq = validate_rna(sequence)
            return translate_rna_to_protein(rna_seq)
        else:
            raise ValueError(f"Invalid sequence type: {sequence_type}")

    async def _embed_with_splitting(self, sequence: str) -> np.ndarray:
        """Embed sequence with splitting for long sequences.

        Args:
            sequence: Protein sequence

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding fails
        """
        if len(sequence) <= MAX_RESIDUES_ESM2:
            return await self.embed_with_cache(sequence)

        windows = self._split_sequence(sequence)
        embeddings = []

        for window in windows:
            embedding = await self.embed_with_cache(window)
            embeddings.append(embedding)

        return np.mean(embeddings, axis=0)

    def _split_sequence(
        self,
        sequence: str,
        window_size: int = 512,
        overlap: int = 256,
    ) -> list[str]:
        """Split long sequence into overlapping windows.

        Args:
            sequence: Protein sequence
            window_size: Window size in residues
            overlap: Overlap between windows

        Returns:
            List of sequence windows
        """
        if len(sequence) > 10000:
            raise SequenceTooLongError(len(sequence), 10000)

        windows = []
        step = window_size - overlap

        for i in range(0, len(sequence), step):
            window = sequence[i : i + window_size]
            if window:
                windows.append(window)

            if i + window_size >= len(sequence):
                break

        return windows

    async def _embed_records(
        self, records: list[SequenceRecord]
    ) -> dict[str, np.ndarray]:
        """Embed multiple sequence records.

        Args:
            records: List of sequence records

        Returns:
            Dictionary of embeddings by ID
        """
        results = {}

        for record in records:
            try:
                protein_seq = validate_protein(record.sequence)
                embedding = await self._embed_with_splitting(protein_seq)
                results[record.id] = embedding
            except Exception as e:
                logger.warning(f"Failed to embed {record.id}: {e}")
                continue

        return results

    def _generate_cache_key(self, input_data: Any) -> str:
        """Generate cache key for sequence.

        Args:
            input_data: Sequence string

        Returns:
            Cache key
        """
        if isinstance(input_data, str):
            sequence_hash = hashlib.md5(input_data.upper().encode()).hexdigest()
            return f"embedding:esm2:seq:{sequence_hash}"

        return super()._generate_cache_key(input_data)
