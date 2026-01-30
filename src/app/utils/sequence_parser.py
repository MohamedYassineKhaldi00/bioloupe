"""Sequence file parsers for FASTA and GenBank formats."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from app.core.sequence_exceptions import (
    InvalidFastaFormatError,
    InvalidGenBankFormatError,
    SequenceParsingError,
)


@dataclass
class SequenceRecord:
    """Parsed sequence record."""

    id: str
    sequence: str
    description: str = ""
    organism: str = ""
    gene: str = ""
    metadata: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class FastaParser:
    """Parser for FASTA format files."""

    def parse_file(self, file_path: str) -> list[SequenceRecord]:
        """Parse FASTA file synchronously.

        Args:
            file_path: Path to FASTA file

        Returns:
            List of sequence records

        Raises:
            InvalidFastaFormatError: If format invalid
            SequenceParsingError: If parsing fails
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise SequenceParsingError(f"File not found: {file_path}")

            content = path.read_text()
            return self.parse_string(content)

        except InvalidFastaFormatError:
            raise
        except Exception as e:
            raise SequenceParsingError(f"Failed to parse FASTA: {str(e)}")

    def parse_string(self, fasta_content: str) -> list[SequenceRecord]:
        """Parse FASTA format string.

        Args:
            fasta_content: FASTA format string

        Returns:
            List of sequence records

        Raises:
            InvalidFastaFormatError: If format invalid
        """
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
                    record = self._build_record(current_header, current_sequence)
                    records.append(record)

                current_header = line[1:]
                current_sequence = []
            else:
                if current_header is None:
                    raise InvalidFastaFormatError("Sequence found before header")
                current_sequence.append(line)

        if current_header is not None:
            record = self._build_record(current_header, current_sequence)
            records.append(record)

        if not records:
            raise InvalidFastaFormatError("No sequences found in FASTA file")

        return records

    def _build_record(self, header: str, sequence_lines: list[str]) -> SequenceRecord:
        """Build sequence record from header and sequence lines.

        Args:
            header: FASTA header line
            sequence_lines: List of sequence lines

        Returns:
            Sequence record
        """
        sequence = "".join(sequence_lines)
        seq_id, description = self._parse_header(header)

        return SequenceRecord(
            id=seq_id,
            sequence=sequence,
            description=description,
        )

    def _parse_header(self, header: str) -> tuple[str, str]:
        """Parse FASTA header into ID and description.

        Args:
            header: Header line without '>'

        Returns:
            Tuple of (ID, description)
        """
        parts = header.split(None, 1)
        seq_id = parts[0] if parts else "unknown"
        description = parts[1] if len(parts) > 1 else ""

        return seq_id, description


class GenBankParser:
    """Parser for GenBank format files."""

    def parse_file(self, file_path: str) -> list[SequenceRecord]:
        """Parse GenBank file.

        Args:
            file_path: Path to GenBank file

        Returns:
            List of sequence records (CDS sequences)

        Raises:
            InvalidGenBankFormatError: If format invalid
            SequenceParsingError: If parsing fails
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise SequenceParsingError(f"File not found: {file_path}")

            content = path.read_text()
            return self.parse_string(content)

        except InvalidGenBankFormatError:
            raise
        except Exception as e:
            raise SequenceParsingError(f"Failed to parse GenBank: {str(e)}")

    def parse_string(self, genbank_content: str) -> list[SequenceRecord]:
        """Parse GenBank format string.

        Args:
            genbank_content: GenBank format string

        Returns:
            List of sequence records

        Raises:
            InvalidGenBankFormatError: If format invalid
        """
        records = []
        organism = self._extract_organism(genbank_content)

        cds_features = self._extract_cds_features(genbank_content)

        for idx, cds_data in enumerate(cds_features):
            record = SequenceRecord(
                id=cds_data.get("locus_tag", f"cds_{idx + 1}"),
                sequence=cds_data["sequence"],
                description=cds_data.get("product", ""),
                organism=organism,
                gene=cds_data.get("gene", ""),
                metadata=cds_data,
            )
            records.append(record)

        if not records:
            raise InvalidGenBankFormatError("No CDS features found in GenBank file")

        return records

    def _extract_organism(self, content: str) -> str:
        """Extract organism from GenBank ORGANISM line."""
        match = re.search(r"ORGANISM\s+(.+)", content)
        return match.group(1).strip() if match else ""

    def _extract_cds_features(self, content: str) -> list[dict[str, str]]:
        """Extract CDS features with translations."""
        cds_list = []
        cds_pattern = r"CDS\s+.*?/translation=\"([^\"]+)\""

        for match in re.finditer(cds_pattern, content, re.DOTALL):
            translation = match.group(1).replace("\n", "").replace(" ", "")
            feature_text = match.group(0)

            gene_match = re.search(r"/gene=\"([^\"]+)\"", feature_text)
            product_match = re.search(r"/product=\"([^\"]+)\"", feature_text)
            locus_match = re.search(r"/locus_tag=\"([^\"]+)\"", feature_text)

            cds_list.append(
                {
                    "sequence": translation,
                    "gene": gene_match.group(1) if gene_match else "",
                    "product": product_match.group(1) if product_match else "",
                    "locus_tag": locus_match.group(1) if locus_match else "",
                }
            )

        return cds_list
