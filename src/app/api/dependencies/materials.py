from __future__ import annotations

from typing import Iterable
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.sessions import require_session_permission
from app.core.exceptions import MaterialNotFound, PermissionDenied
from app.db.base import get_db
from app.models import Material, SessionPermission


async def get_material(material_id: str, db: AsyncSession = Depends(get_db)) -> Material:
    material = await db.get(Material, material_id)
    if not material or material.deleted_at is not None:
        raise MaterialNotFound(material_id)
    return material


async def require_material_permission(
    material_id: str,
    required_permissions: Iterable[SessionPermission],
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Material:
    material = await get_material(material_id, db)
    await require_session_permission(material.session_id, required_permissions, current_user, db)
    return material


def material_permission_required(required_permissions: Iterable[SessionPermission]):
    async def dependency(
        material_id: str,
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> Material:
        return await require_material_permission(material_id, required_permissions, current_user, db)

    return dependency
