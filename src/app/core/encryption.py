"""Encryption service for data at rest."""

from __future__ import annotations

import logging
import base64
from typing import Any

logger = logging.getLogger(__name__)


class EncryptionService:
    """Handle encryption and decryption of sensitive data."""

    def __init__(self, master_key: str):
        """Initialize with master encryption key from environment."""
        # In production, use cryptography.fernet or similar
        self.key = master_key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt string, return base64 encoded ciphertext."""
        if not plaintext:
            return plaintext

        # Placeholder encryption
        # In production: use Fernet or AES-GCM
        encoded = base64.b64encode(plaintext.encode()).decode()
        return f"ENC:{encoded}"

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64 encoded ciphertext."""
        if not ciphertext or not ciphertext.startswith("ENC:"):
            return ciphertext

        # Placeholder decryption
        encoded = ciphertext[4:]  # Remove "ENC:" prefix
        decoded = base64.b64decode(encoded).decode()
        return decoded

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        # Placeholder - use bcrypt in production
        import hashlib

        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        # Placeholder - use bcrypt.checkpw in production
        return self.hash_password(password) == hashed

    def rotate_key(
        self, old_key: str, new_key: str, encrypted_values: list[str]
    ) -> list[str]:
        """Re-encrypt values with new key."""
        old_service = EncryptionService(old_key)
        new_service = EncryptionService(new_key)

        re_encrypted = []
        for value in encrypted_values:
            try:
                decrypted = old_service.decrypt(value)
                encrypted = new_service.encrypt(decrypted)
                re_encrypted.append(encrypted)
            except Exception as e:
                logger.error(f"Key rotation failed for value: {e}")
                re_encrypted.append(value)

        return re_encrypted


class FieldEncryptionHelper:
    """Helper for field-level encryption in database models."""

    def __init__(self, encryption_service: EncryptionService):
        self.encryption = encryption_service

    def encrypt_field(self, value: Any) -> str | None:
        """Encrypt field value before storing."""
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        return self.encryption.encrypt(value)

    def decrypt_field(self, value: str | None) -> str | None:
        """Decrypt field value when retrieving."""
        if value is None:
            return None

        return self.encryption.decrypt(value)

    def encrypt_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Encrypt all string values in dictionary."""
        encrypted = {}

        for key, value in data.items():
            if isinstance(value, str):
                encrypted[key] = self.encrypt_field(value)
            elif isinstance(value, dict):
                encrypted[key] = self.encrypt_dict(value)
            else:
                encrypted[key] = value

        return encrypted

    def decrypt_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Decrypt all encrypted values in dictionary."""
        decrypted = {}

        for key, value in data.items():
            if isinstance(value, str) and value.startswith("ENC:"):
                decrypted[key] = self.decrypt_field(value)
            elif isinstance(value, dict):
                decrypted[key] = self.decrypt_dict(value)
            else:
                decrypted[key] = value

        return decrypted
