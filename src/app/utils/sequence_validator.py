"""Sequence validation utilities."""

from __future__ import annotations

import re
from typing import Literal

from app.core.sequence_exceptions import InvalidSequenceError, SequenceTooLongError

# Standard amino acid alphabet
PROTEIN_ALPHABET = set("ACDEFGHIKLMNPQRSTVWY")
# Extended amino acids (ambiguous)
EXTENDED_PROTEIN_ALPHABET = PROTEIN_ALPHABET | {"B", "Z", "X"}
# DNA alphabet
DNA_ALPHABET = set("ATGC")
# RNA alphabet
RNA_ALPHABET = set("AUGC")
# Allowed special characters
ALLOWED_GAPS = {"-", "."}
ALLOWED_STOPS = {"*"}

# Maximum lengths
MAX_RESIDUES_TOTAL = 10000
MAX_RESIDUES_ESM2 = 1024

SequenceType = Literal["protein", "dna", "rna"]


def clean_sequence(sequence: str) -> str:
    """Remove gaps and stop codons from sequence.

    Args:
        sequence: Raw sequence string

    Returns:
        Cleaned uppercase sequence
    """
    sequence = sequence.upper().strip()
    sequence = re.sub(r"[-.*\s]", "", sequence)
    return sequence


def validate_protein(
    sequence: str, allow_extended: bool = True, max_length: int = MAX_RESIDUES_TOTAL
) -> str:
    """Validate protein sequence.

    Args:
        sequence: Protein sequence
        allow_extended: Allow ambiguous amino acids (B, Z, X)
        max_length: Maximum allowed length

    Returns:
        Cleaned sequence

    Raises:
        InvalidSequenceError: If invalid characters found
        SequenceTooLongError: If sequence too long
    """
    cleaned = clean_sequence(sequence)

    if not cleaned:
        raise InvalidSequenceError("Sequence is empty after cleaning")

    if len(cleaned) > max_length:
        raise SequenceTooLongError(len(cleaned), max_length)

    alphabet = EXTENDED_PROTEIN_ALPHABET if allow_extended else PROTEIN_ALPHABET
    invalid_chars = set(cleaned) - alphabet

    if invalid_chars:
        raise InvalidSequenceError(
            f"Invalid protein characters: {', '.join(sorted(invalid_chars))}"
        )

    return cleaned


def validate_dna(sequence: str, max_length: int = MAX_RESIDUES_TOTAL * 3) -> str:
    """Validate DNA sequence.

    Args:
        sequence: DNA sequence
        max_length: Maximum allowed length

    Returns:
        Cleaned sequence

    Raises:
        InvalidSequenceError: If invalid characters found
        SequenceTooLongError: If sequence too long
    """
    cleaned = clean_sequence(sequence)

    if not cleaned:
        raise InvalidSequenceError("Sequence is empty after cleaning")

    if len(cleaned) > max_length:
        raise SequenceTooLongError(len(cleaned), max_length)

    invalid_chars = set(cleaned) - DNA_ALPHABET

    if invalid_chars:
        raise InvalidSequenceError(
            f"Invalid DNA characters: {', '.join(sorted(invalid_chars))}"
        )

    return cleaned


def validate_rna(sequence: str, max_length: int = MAX_RESIDUES_TOTAL * 3) -> str:
    """Validate RNA sequence.

    Args:
        sequence: RNA sequence
        max_length: Maximum allowed length

    Returns:
        Cleaned sequence

    Raises:
        InvalidSequenceError: If invalid characters found
        SequenceTooLongError: If sequence too long
    """
    cleaned = clean_sequence(sequence)

    if not cleaned:
        raise InvalidSequenceError("Sequence is empty after cleaning")

    if len(cleaned) > max_length:
        raise SequenceTooLongError(len(cleaned), max_length)

    invalid_chars = set(cleaned) - RNA_ALPHABET

    if invalid_chars:
        raise InvalidSequenceError(
            f"Invalid RNA characters: {', '.join(sorted(invalid_chars))}"
        )

    return cleaned


def translate_dna_to_protein(dna_sequence: str) -> str:
    """Translate DNA sequence to protein.

    Args:
        dna_sequence: DNA sequence (cleaned)

    Returns:
        Protein sequence

    Raises:
        InvalidSequenceError: If sequence length not multiple of 3
    """
    if len(dna_sequence) % 3 != 0:
        raise InvalidSequenceError("DNA sequence length must be multiple of 3")

    codon_table = _get_codon_table()
    protein = []

    for i in range(0, len(dna_sequence), 3):
        codon = dna_sequence[i : i + 3]
        amino_acid = codon_table.get(codon, "X")
        if amino_acid != "*":
            protein.append(amino_acid)

    return "".join(protein)


def translate_rna_to_protein(rna_sequence: str) -> str:
    """Translate RNA sequence to protein.

    Args:
        rna_sequence: RNA sequence (cleaned)

    Returns:
        Protein sequence
    """
    dna_sequence = rna_sequence.replace("U", "T")
    return translate_dna_to_protein(dna_sequence)


def _get_codon_table() -> dict[str, str]:
    """Get standard genetic code codon table.

    Returns:
        Dictionary mapping codons to amino acids
    """
    return {
        "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
        "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
        "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
        "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
        "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
        "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
        "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
        "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
        "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
        "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
        "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
        "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
        "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
        "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
        "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
        "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
    }
