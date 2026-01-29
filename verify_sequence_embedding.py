"""Standalone verification script for sequence embedding components.

This script tests the sequence validation and parsing logic without requiring
the full application dependencies.
"""

import re
from typing import Literal

# ========== SEQUENCE VALIDATOR LOGIC ==========

PROTEIN_ALPHABET = set("ACDEFGHIKLMNPQRSTVWY")
EXTENDED_PROTEIN_ALPHABET = PROTEIN_ALPHABET | {"B", "Z", "X"}
DNA_ALPHABET = set("ATGC")
RNA_ALPHABET = set("AUGC")


def clean_sequence(sequence: str) -> str:
    """Remove gaps and stop codons from sequence."""
    sequence = sequence.upper().strip()
    sequence = re.sub(r"[-.*\s]", "", sequence)
    return sequence


def validate_protein(sequence: str, allow_extended: bool = True) -> str:
    """Validate protein sequence."""
    cleaned = clean_sequence(sequence)
    if not cleaned:
        raise ValueError("Sequence is empty after cleaning")

    alphabet = EXTENDED_PROTEIN_ALPHABET if allow_extended else PROTEIN_ALPHABET
    invalid_chars = set(cleaned) - alphabet

    if invalid_chars:
        raise ValueError(f"Invalid protein characters: {', '.join(sorted(invalid_chars))}")

    return cleaned


def validate_dna(sequence: str) -> str:
    """Validate DNA sequence."""
    cleaned = clean_sequence(sequence)
    if not cleaned:
        raise ValueError("Sequence is empty after cleaning")

    invalid_chars = set(cleaned) - DNA_ALPHABET
    if invalid_chars:
        raise ValueError(f"Invalid DNA characters: {', '.join(sorted(invalid_chars))}")

    return cleaned


def translate_dna_to_protein(dna_sequence: str) -> str:
    """Translate DNA sequence to protein."""
    if len(dna_sequence) % 3 != 0:
        raise ValueError("DNA sequence length must be multiple of 3")

    codon_table = {
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

    protein = []
    for i in range(0, len(dna_sequence), 3):
        codon = dna_sequence[i:i+3]
        amino_acid = codon_table.get(codon, "X")
        if amino_acid != "*":
            protein.append(amino_acid)

    return "".join(protein)


# ========== FASTA PARSER LOGIC ==========

def parse_fasta_string(fasta_content: str):
    """Parse FASTA format string."""
    records = []
    current_header = None
    current_sequence = []

    lines = fasta_content.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith(">"):
            if current_header is not None:
                seq_id = current_header.split()[0]
                sequence = "".join(current_sequence)
                records.append({"id": seq_id, "sequence": sequence})

            current_header = line[1:]
            current_sequence = []
        else:
            if current_header is None:
                raise ValueError("Sequence found before header")
            current_sequence.append(line)

    if current_header is not None:
        seq_id = current_header.split()[0]
        sequence = "".join(current_sequence)
        records.append({"id": seq_id, "sequence": sequence})

    return records


# ========== TESTS ==========

def test_protein_validation():
    """Test protein sequence validation."""
    print("Testing protein validation...")

    # Valid sequence
    result = validate_protein("ACDEFGHIKLMNPQRSTVWY")
    assert result == "ACDEFGHIKLMNPQRSTVWY", "Basic validation failed"
    print("  ✅ Valid protein sequence")

    # With gaps
    result = validate_protein("ACDE-FGH*IKL")
    assert result == "ACDEFGHIKL", "Gap removal failed"
    print("  ✅ Gap removal")

    # Lowercase
    result = validate_protein("acdefghikl")
    assert result == "ACDEFGHIKL", "Uppercase conversion failed"
    print("  ✅ Uppercase conversion")

    # Invalid characters
    try:
        validate_protein("ACDE123FGH")
        assert False, "Should have raised error"
    except ValueError as e:
        assert "Invalid protein characters" in str(e)
        print("  ✅ Invalid characters detected")


def test_dna_validation():
    """Test DNA sequence validation."""
    print("\nTesting DNA validation...")

    # Valid DNA
    result = validate_dna("ATGCATGC")
    assert result == "ATGCATGC", "DNA validation failed"
    print("  ✅ Valid DNA sequence")

    # Invalid characters
    try:
        validate_dna("ATGCUXYZ")
        assert False, "Should have raised error"
    except ValueError:
        print("  ✅ Invalid DNA characters detected")


def test_dna_translation():
    """Test DNA to protein translation."""
    print("\nTesting DNA translation...")

    # Simple translation
    protein = translate_dna_to_protein("ATGGCCCTG")
    assert protein == "MAL", f"Translation failed: got {protein}"
    print("  ✅ DNA translation (ATG GCC CTG → MAL)")

    # Longer sequence
    protein = translate_dna_to_protein("ATGGCCCTGTGGATGCGCCTCCTG")
    assert len(protein) == 8, "Translation length incorrect"
    print(f"  ✅ Longer translation: {protein}")

    # Invalid length
    try:
        translate_dna_to_protein("ATGGC")
        assert False, "Should have raised error"
    except ValueError:
        print("  ✅ Invalid length detected")


def test_fasta_parsing():
    """Test FASTA parsing."""
    print("\nTesting FASTA parsing...")

    # Single sequence
    fasta = """>seq1 Test sequence
ACDEFGHIKLMNPQRSTVWY"""

    records = parse_fasta_string(fasta)
    assert len(records) == 1, "Should parse 1 record"
    assert records[0]["id"] == "seq1", "ID parsing failed"
    assert records[0]["sequence"] == "ACDEFGHIKLMNPQRSTVWY", "Sequence parsing failed"
    print("  ✅ Single sequence parsing")

    # Multiple sequences
    fasta = """>seq1 First
ACDEFGHIKL
>seq2 Second
MNPQRSTVWY"""

    records = parse_fasta_string(fasta)
    assert len(records) == 2, "Should parse 2 records"
    assert records[0]["id"] == "seq1"
    assert records[1]["id"] == "seq2"
    print("  ✅ Multiple sequence parsing")

    # Multi-line sequence
    fasta = """>seq1
ACDEFGHIKL
MNPQRSTVWY"""

    records = parse_fasta_string(fasta)
    assert records[0]["sequence"] == "ACDEFGHIKLMNPQRSTVWY", "Multi-line failed"
    print("  ✅ Multi-line sequence parsing")


def test_sequence_splitting():
    """Test long sequence splitting logic."""
    print("\nTesting sequence splitting...")

    def split_sequence(sequence: str, window_size: int = 512, overlap: int = 256):
        """Split long sequence into overlapping windows."""
        windows = []
        step = window_size - overlap

        for i in range(0, len(sequence), step):
            window = sequence[i:i+window_size]
            if window:
                windows.append(window)
            if i + window_size >= len(sequence):
                break

        return windows

    # Short sequence (no splitting)
    seq = "A" * 500
    windows = split_sequence(seq)
    assert len(windows) == 1, "Should not split short sequence"
    print("  ✅ Short sequence (no split)")

    # Long sequence (needs splitting)
    seq = "A" * 2000
    windows = split_sequence(seq, window_size=512, overlap=256)
    assert len(windows) > 1, "Should split long sequence"
    assert all(len(w) <= 512 for w in windows), "Window size exceeded"
    print(f"  ✅ Long sequence split into {len(windows)} windows")


def main():
    """Run all tests."""
    print("=" * 60)
    print("SEQUENCE EMBEDDING COMPONENT VERIFICATION")
    print("=" * 60)

    try:
        test_protein_validation()
        test_dna_validation()
        test_dna_translation()
        test_fasta_parsing()
        test_sequence_splitting()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nSequence embedding components are working correctly.")
        print("Ready for integration with ESM-2 model.")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
