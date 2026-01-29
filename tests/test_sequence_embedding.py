"""Tests for sequence embedding service."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from app.core.ml_config import SEQUENCE_EMBEDDING_CONFIG
from app.core.sequence_exceptions import (
    InvalidSequenceError,
    SequenceTooLongError,
)
from app.services.embedding.sequence_embedding import SequenceEmbeddingService
from app.utils.sequence_parser import FastaParser
from app.utils.sequence_validator import (
    validate_protein,
    validate_dna,
    validate_rna,
    translate_dna_to_protein,
)


@pytest.fixture
def mock_service():
    """Create mocked sequence embedding service."""
    service = SequenceEmbeddingService(SEQUENCE_EMBEDDING_CONFIG)
    service._model = MagicMock()
    service._tokenizer = MagicMock()
    service._is_loaded = True
    return service


@pytest.mark.asyncio
async def test_embed_protein_sequence(mock_service):
    """Test embedding a protein sequence."""
    sequence = "ACDEFGHIKLMNPQRSTVWY"

    with patch.object(
        mock_service, "_embed_with_splitting", new_callable=AsyncMock
    ) as mock_embed:
        mock_embed.return_value = np.random.rand(1280)

        embedding = await mock_service.embed_sequence(sequence, "protein")

        assert embedding.shape == (1280,)
        mock_embed.assert_called_once()


@pytest.mark.asyncio
async def test_embed_dna_sequence(mock_service):
    """Test embedding a DNA sequence (translated to protein)."""
    dna_sequence = "ATGGCCCTGTGGATG"

    with patch.object(
        mock_service, "_embed_with_splitting", new_callable=AsyncMock
    ) as mock_embed:
        mock_embed.return_value = np.random.rand(1280)

        embedding = await mock_service.embed_sequence(dna_sequence, "dna")

        assert embedding.shape == (1280,)
        mock_embed.assert_called_once()


@pytest.mark.asyncio
async def test_embed_rna_sequence(mock_service):
    """Test embedding an RNA sequence."""
    rna_sequence = "AUGGCCCUGUGGAUG"

    with patch.object(
        mock_service, "_embed_with_splitting", new_callable=AsyncMock
    ) as mock_embed:
        mock_embed.return_value = np.random.rand(1280)

        embedding = await mock_service.embed_sequence(rna_sequence, "rna")

        assert embedding.shape == (1280,)
        mock_embed.assert_called_once()


@pytest.mark.asyncio
async def test_embed_long_sequence(mock_service):
    """Test embedding a long sequence with splitting."""
    long_sequence = "A" * 2000

    with patch.object(mock_service, "embed_with_cache", new_callable=AsyncMock) as mock_cache:
        mock_cache.return_value = np.random.rand(1280)

        embedding = await mock_service._embed_with_splitting(long_sequence)

        assert embedding.shape == (1280,)
        assert mock_cache.call_count > 1


def test_validate_protein_valid():
    """Test validating a valid protein sequence."""
    sequence = "ACDEFGHIKLMNPQRSTVWY"
    result = validate_protein(sequence)
    assert result == sequence


def test_validate_protein_with_gaps():
    """Test validating protein with gaps."""
    sequence = "ACDE-FGH-IKL"
    result = validate_protein(sequence)
    assert result == "ACDEFGHIKL"


def test_validate_protein_invalid():
    """Test validating protein with invalid characters."""
    sequence = "ACDE123FGH"
    with pytest.raises(InvalidSequenceError):
        validate_protein(sequence)


def test_validate_protein_too_long():
    """Test validating protein that's too long."""
    sequence = "A" * 10001
    with pytest.raises(SequenceTooLongError):
        validate_protein(sequence)


def test_validate_dna_valid():
    """Test validating valid DNA sequence."""
    sequence = "ATGCATGC"
    result = validate_dna(sequence)
    assert result == sequence


def test_validate_dna_invalid():
    """Test validating DNA with invalid characters."""
    sequence = "ATGCUXYZ"
    with pytest.raises(InvalidSequenceError):
        validate_dna(sequence)


def test_validate_rna_valid():
    """Test validating valid RNA sequence."""
    sequence = "AUGCAUGC"
    result = validate_rna(sequence)
    assert result == sequence


def test_translate_dna_to_protein():
    """Test DNA to protein translation."""
    dna = "ATGGCCCTG"
    protein = translate_dna_to_protein(dna)
    assert protein == "MAL"


def test_translate_dna_invalid_length():
    """Test DNA translation with invalid length."""
    dna = "ATGGC"
    with pytest.raises(InvalidSequenceError):
        translate_dna_to_protein(dna)


def test_fasta_parser():
    """Test FASTA format parsing."""
    fasta_content = """>seq1 Test sequence 1
ACDEFGHIKLMNPQRSTVWY
>seq2 Test sequence 2
MALWMRLLPLLALLALWGPD
"""
    parser = FastaParser()
    records = parser.parse_string(fasta_content)

    assert len(records) == 2
    assert records[0].id == "seq1"
    assert records[0].sequence == "ACDEFGHIKLMNPQRSTVWY"
    assert records[1].id == "seq2"


def test_fasta_parser_multiline():
    """Test FASTA with multi-line sequences."""
    fasta_content = """>seq1
ACDEFGHIKL
MNPQRSTVWY
"""
    parser = FastaParser()
    records = parser.parse_string(fasta_content)

    assert len(records) == 1
    assert records[0].sequence == "ACDEFGHIKLMNPQRSTVWY"


def test_split_sequence():
    """Test sequence splitting for long sequences."""
    service = SequenceEmbeddingService(SEQUENCE_EMBEDDING_CONFIG)
    sequence = "A" * 2000

    windows = service._split_sequence(sequence, window_size=512, overlap=256)

    assert len(windows) > 1
    assert all(len(w) <= 512 for w in windows)


def test_split_sequence_too_long():
    """Test splitting rejects extremely long sequences."""
    service = SequenceEmbeddingService(SEQUENCE_EMBEDDING_CONFIG)
    sequence = "A" * 10001

    with pytest.raises(SequenceTooLongError):
        service._split_sequence(sequence)


@pytest.mark.asyncio
async def test_embed_from_material(mock_service):
    """Test embedding from material object."""
    from app.models.material import Material

    material = MagicMock(spec=Material)
    material.metadata_ = {
        "sequence": "ACDEFGHIKLMNPQRSTVWY",
        "sequence_type": "protein"
    }

    with patch.object(
        mock_service, "embed_sequence", new_callable=AsyncMock
    ) as mock_embed:
        mock_embed.return_value = np.random.rand(1280)

        embedding = await mock_service.embed_from_material(material)

        assert embedding.shape == (1280,)
        mock_embed.assert_called_once_with("ACDEFGHIKLMNPQRSTVWY", "protein")
