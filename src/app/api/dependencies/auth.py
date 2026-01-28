from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDenied
from app.core.security import decode_token
from app.db.base import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    subject = payload.get("sub")
    if not subject:
        raise PermissionDenied("Invalid authentication token")

    result = await db.execute(select(User).where(User.id == subject))
    user = result.scalar_one_or_none()
    if not user:
        raise PermissionDenied("Invalid authentication token")
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active or not current_user.is_verified:
        raise PermissionDenied("Inactive user")
    return current_user
