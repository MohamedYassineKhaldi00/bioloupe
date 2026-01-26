from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from ...app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, email: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": subject,
        "email": email,
        "type": "access",
        "exp": expire,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": expire,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def validate_token_type(payload: dict[str, Any], expected_type: str) -> bool:
    return payload.get("type") == expected_type


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/"
    if not any(char in special_chars for char in password):
        return False, "Password must contain at least one special character"

    return True, "Password is valid"
