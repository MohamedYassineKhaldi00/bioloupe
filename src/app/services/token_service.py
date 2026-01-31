from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import InvalidToken
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_token_type,
)
from app.db.redis_client import get_redis
from app.schemas.auth_schemas import TokenResponse


async def generate_token_pair(user_id: uuid.UUID, email: str) -> TokenResponse:
    access_token = create_access_token(str(user_id), email)
    refresh_token = create_refresh_token(str(user_id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


async def blacklist_refresh_token(token: str) -> None:
    redis = get_redis()
    await redis.setex(f"blacklist:refresh:{token}", 604800, "1")


async def is_token_blacklisted(token: str) -> bool:
    redis = get_redis()
    result = await redis.get(f"blacklist:refresh:{token}")
    return result is not None


def validate_and_decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = decode_token(token)
    except Exception:
        raise InvalidToken()

    if not validate_token_type(payload, expected_type):
        raise InvalidToken()

    return payload


def extract_user_id_from_payload(payload: dict[str, Any]) -> uuid.UUID:
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise InvalidToken()

    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        raise InvalidToken()


def generate_email_verification_token(user_id: uuid.UUID) -> str:
    from jose import jwt

    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=24)

    payload = {
        "sub": str(user_id),
        "type": "email_verification",
        "exp": expire,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def generate_password_reset_token(user_id: uuid.UUID) -> str:
    from jose import jwt

    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=1)

    payload = {
        "sub": str(user_id),
        "type": "password_reset",
        "exp": expire,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
