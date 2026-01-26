from __future__ import annotations

import uuid
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....app.core.security import hash_password, validate_password_strength
from ....app.db.base import get_db
from ....app.models.user import User
from ....app.schemas.auth_schemas import RegisterRequest


async def create_user_account(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    is_valid, message = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if request.orcid_id:
        result = await db.execute(select(User).where(User.orcid_id == request.orcid_id))
        existing_orcid = result.scalar_one_or_none()
        if existing_orcid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ORCID ID already registered"
            )

    new_user = User(
        id=uuid.uuid4(),
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        orcid_id=request.orcid_id,
        is_active=True,
        is_verified=False,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


async def authenticate_user_credentials(email: str, password: str, db: AsyncSession) -> User:
    from ....app.core.exceptions import InvalidCredentials
    from ....app.core.security import verify_password

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise InvalidCredentials()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def mark_email_verified(user_id: uuid.UUID, db: AsyncSession) -> User:
    from ....app.core.exceptions import InvalidToken

    user = await get_user_by_id(user_id, db)
    if not user:
        raise InvalidToken()

    user.is_verified = True
    await db.commit()
    await db.refresh(user)

    return user


async def update_user_password(user_id: uuid.UUID, new_password: str, db: AsyncSession) -> User:
    from ....app.core.exceptions import InvalidToken

    is_valid, message = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    user = await get_user_by_id(user_id, db)
    if not user:
        raise InvalidToken()

    user.hashed_password = hash_password(new_password)
    await db.commit()
    await db.refresh(user)

    return user
