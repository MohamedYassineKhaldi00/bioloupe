from __future__ import annotations

import uuid
from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidToken, InactiveUser, EmailNotVerified
from app.core.security import decode_token, validate_token_type
from app.db.base import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = decode_token(token)
    except Exception:
        raise InvalidToken()

    if not validate_token_type(payload, "access"):
        raise InvalidToken()

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise InvalidToken()

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise InvalidToken()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise InvalidToken()

    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_active:
        raise InactiveUser()

    if not current_user.is_verified:
        raise EmailNotVerified()

    return current_user
