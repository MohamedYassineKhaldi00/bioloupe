"""Sequence-specific exceptions."""

from __future__ import annotations

from fastapi import status

from app.core.exceptions import BioLoupeException


class InvalidSequenceError(BioLoupeException):
    """Raised when sequence contains invalid characters."""

    def __init__(self, message: str = "Invalid sequence characters") -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class SequenceTooLongError(BioLoupeException):
    """Raised when sequence exceeds maximum length."""

    def __init__(
        self,
        length: int,
        max_length: int = 10000,
        message: str | None = None,
    ) -> None:
        msg = message or f"Sequence length {length} exceeds maximum {max_length}"
        super().__init__(msg, status.HTTP_400_BAD_REQUEST)


class InvalidFastaFormatError(BioLoupeException):
    """Raised when FASTA file format is invalid."""

    def __init__(self, message: str = "Invalid FASTA format") -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class InvalidGenBankFormatError(BioLoupeException):
    """Raised when GenBank file format is invalid."""

    def __init__(self, message: str = "Invalid GenBank format") -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class SequenceParsingError(BioLoupeException):
    """Raised when sequence parsing fails."""

    def __init__(self, message: str = "Failed to parse sequence file") -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST)
