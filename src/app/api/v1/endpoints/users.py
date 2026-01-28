from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.core.exceptions import ResourceNotFound
from app.db.base import get_db
from app.models import User
from app.schemas.user_schemas import UserPublic, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.orcid_id is not None:
        current_user.orcid_id = payload.orcid_id
    await db.flush()
    return current_user


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ResourceNotFound("User", user_id)
    return user
