"""Text preprocessing for scientific papers."""

from __future__ import annotations

import re
from typing import Any


class ScientificTextPreprocessor:
    """Preprocess scientific paper text for embeddings."""

    LATEX_PATTERN = re.compile(
        r"\\[a-zA-Z]+\{[^}]*\}|\\[a-zA-Z]+|\$[^$]*\$|\$\$[^$]*\$\$"
    )
    SPECIAL_CHARS_PATTERN = re.compile(r"[^\w\s.,;:!?-]")
    WHITESPACE_PATTERN = re.compile(r"\s+")

    def __init__(self, tokenizer: Any) -> None:
        """Initialize preprocessor.

        Args:
            tokenizer: HuggingFace tokenizer
        """
        self.tokenizer = tokenizer

    def preprocess(
        self,
        text: str,
        lowercase: bool = True,
        remove_latex: bool = True,
        remove_special: bool = True,
    ) -> str:
        """Preprocess text.

        Args:
            text: Input text
            lowercase: Whether to lowercase
            remove_latex: Whether to remove LaTeX
            remove_special: Whether to remove special chars

        Returns:
            Preprocessed text
        """
        if lowercase:
            text = text.lower()

        if remove_latex:
            text = self._remove_latex(text)

        if remove_special:
            text = self._remove_special_chars(text)

        text = self._normalize_whitespace(text)

        return text.strip()

    def _remove_latex(self, text: str) -> str:
        """Remove LaTeX commands.

        Args:
            text: Input text

        Returns:
            Text without LaTeX
        """
        return self.LATEX_PATTERN.sub(" ", text)

    def _remove_special_chars(self, text: str) -> str:
        """Remove special characters.

        Args:
            text: Input text

        Returns:
            Text without special chars
        """
        return self.SPECIAL_CHARS_PATTERN.sub(" ", text)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        return self.WHITESPACE_PATTERN.sub(" ", text)

    def truncate_to_tokens(
        self, text: str, max_tokens: int = 512
    ) -> str:
        """Truncate text to max tokens.

        Args:
            text: Input text
            max_tokens: Maximum token count

        Returns:
            Truncated text
        """
        tokens = self.tokenizer.encode(
            text, add_special_tokens=False, truncation=False
        )

        if len(tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(
            truncated_tokens, skip_special_tokens=True
        )

    def combine_paper_parts(
        self,
        title: str,
        abstract: str,
        introduction: str = "",
        max_tokens: int = 512,
    ) -> str:
        """Combine paper parts with priority.

        Args:
            title: Paper title
            abstract: Paper abstract
            introduction: Paper introduction
            max_tokens: Maximum tokens

        Returns:
            Combined text
        """
        title_clean = self.preprocess(title)
        abstract_clean = self.preprocess(abstract)
        intro_clean = self.preprocess(introduction) if introduction else ""

        combined = f"{title_clean} [SEP] {abstract_clean}"

        if intro_clean:
            combined = f"{combined} [SEP] {intro_clean}"

        return self.truncate_to_tokens(combined, max_tokens)
