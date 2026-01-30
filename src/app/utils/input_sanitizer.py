"""Input sanitization utilities for security."""

from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Sanitize user inputs to prevent injection attacks."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Remove potentially dangerous characters."""
        if not value:
            return value

        # Remove null bytes
        value = value.replace("\x00", "")

        # Trim to max length
        value = value[:max_length]

        # Remove control characters except newline, tab
        value = "".join(
            char for char in value if char.isprintable() or char in "\n\t"
        )

        return value.strip()

    @staticmethod
    def sanitize_html(value: str) -> str:
        """Strip HTML tags for basic sanitization."""
        if not value:
            return value

        # Remove HTML tags (basic approach)
        # In production, use library like bleach
        cleaned = re.sub(r"<[^>]+>", "", value)

        return cleaned

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(pattern, email):
            raise ValueError("Invalid email format")

        return email.lower()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        if not filename:
            return filename

        # Keep only basename
        filename = filename.split("/")[-1].split("\\")[-1]

        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", filename)

        # Prevent hidden files
        if filename.startswith("."):
            filename = filename[1:]

        # Limit length
        filename = filename[:255]

        return filename if filename else "unnamed"

    @staticmethod
    def validate_url(url: str, allowed_schemes: list[str] | None = None) -> str:
        """Validate URL format and scheme."""
        if allowed_schemes is None:
            allowed_schemes = ["http", "https"]

        # Basic URL validation
        url_pattern = r"^(https?://)[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$"

        if not re.match(url_pattern, url):
            raise ValueError("Invalid URL format")

        scheme = url.split("://")[0]
        if scheme not in allowed_schemes:
            raise ValueError(f"URL scheme must be one of: {allowed_schemes}")

        return url

    @staticmethod
    def sanitize_json_keys(data: dict[str, Any]) -> dict[str, Any]:
        """Sanitize dictionary keys to prevent injection."""
        sanitized = {}

        for key, value in data.items():
            # Only allow alphanumeric and underscore in keys
            clean_key = re.sub(r"[^a-zA-Z0-9_]", "", key)

            if isinstance(value, dict):
                sanitized[clean_key] = InputSanitizer.sanitize_json_keys(value)
            elif isinstance(value, str):
                sanitized[clean_key] = InputSanitizer.sanitize_string(value)
            else:
                sanitized[clean_key] = value

        return sanitized
