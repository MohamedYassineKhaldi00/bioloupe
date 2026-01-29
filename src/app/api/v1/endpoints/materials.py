from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.materials import material_permission_required, require_material_permission
from app.api.dependencies.sessions import require_session_permission
from app.db.base import get_db
from app.models import Material, MaterialType, SessionParticipant, SessionPermission, User
from app.schemas.material_schemas import (
    MaterialBatchCreate,
    MaterialBatchUpdate,
    MaterialCreate,
    MaterialResponse,
    MaterialTagUpdate,
    MaterialUpdate,
    MaterialUploadComplete,
    MaterialUploadInitiate,
    MaterialUploadInitiateResponse,
)
from app.services.material_service import MaterialService
from app.services.upload_service import UploadService

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("/search", response_model=list[MaterialResponse])
async def search_materials(
    q: str,
    session_id: str | None = None,
    material_type: MaterialType | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[MaterialResponse]:
    if session_id:
        await require_session_permission(session_id, [SessionPermission.read], current_user, db)
    service = MaterialService(db)
    materials = await service.search_materials(q, session_id, material_type)
    if not session_id:
        session_result = await db.execute(
            select(SessionParticipant.session_id).where(SessionParticipant.user_id == current_user.id)
        )
        session_ids = {row[0] for row in session_result.all()}
        materials = [material for material in materials if material.session_id in session_ids]
    return [MaterialResponse.model_validate(material) for material in materials]


@router.post("", response_model=MaterialResponse)
async def create_material(
    payload: MaterialCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaterialResponse:
    await require_session_permission(payload.session_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = MaterialService(db)
    material = await service.create_material(payload, str(current_user.id))
    return MaterialResponse.model_validate(material)


@router.post("/batch", response_model=list[MaterialResponse])
async def batch_create_materials(
    payload: MaterialBatchCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[MaterialResponse]:
    await require_session_permission(payload.session_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = MaterialService(db)
    materials = []
    for item in payload.materials:
        material = await service.create_material(item, str(current_user.id))
        materials.append(MaterialResponse.model_validate(material))
    return materials


@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material_details(
    material_id: str,
    _material=Depends(material_permission_required([SessionPermission.read])),
    db: AsyncSession = Depends(get_db),
) -> MaterialResponse:
    material = await db.get(Material, material_id)
    return MaterialResponse.model_validate(material)


@router.patch("/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: str,
    payload: MaterialUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaterialResponse:
    await require_material_permission(material_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = MaterialService(db)
    material = await service.update_material(material_id, payload, str(current_user.id))
    return MaterialResponse.model_validate(material)


@router.delete("/{material_id}")
async def delete_material(
    material_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_material_permission(material_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = MaterialService(db)
    await service.soft_delete(material_id, str(current_user.id))
    return {"status": "deleted"}


@router.post("/{material_id}/restore")
async def restore_material(
    material_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_material_permission(material_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = MaterialService(db)
    await service.restore(material_id, str(current_user.id))
    return {"status": "restored"}


@router.post("/{material_id}/tags", response_model=MaterialResponse)
async def add_tags(
    material_id: str,
    payload: MaterialTagUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaterialResponse:
    await require_material_permission(material_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = MaterialService(db)
    material = await service.add_tags(material_id, payload.tags, str(current_user.id))
    return MaterialResponse.model_validate(material)


@router.delete("/{material_id}/tags", response_model=MaterialResponse)
async def remove_tags(
    material_id: str,
    payload: MaterialTagUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaterialResponse:
    await require_material_permission(material_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = MaterialService(db)
    material = await service.remove_tags(material_id, payload.tags, str(current_user.id))
    return MaterialResponse.model_validate(material)


@router.patch("/batch-update", response_model=list[MaterialResponse])
async def batch_update_materials(
    payload: MaterialBatchUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[MaterialResponse]:
    service = MaterialService(db)
    for item in payload.updates:
        await require_material_permission(item.material_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    materials = await service.batch_update(payload.updates, str(current_user.id))
    return [MaterialResponse.model_validate(material) for material in materials]


@router.post("/upload/initiate", response_model=MaterialUploadInitiateResponse)
async def initiate_upload(
    payload: MaterialUploadInitiate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaterialUploadInitiateResponse:
    await require_session_permission(payload.session_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = UploadService(db)
    result = await service.initiate_upload(payload, str(current_user.id))
    return MaterialUploadInitiateResponse(**result)


@router.post("/upload/{material_id}/complete", response_model=MaterialResponse)
async def complete_upload(
    material_id: str,
    payload: MaterialUploadComplete,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaterialResponse:
    await require_material_permission(material_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = UploadService(db)
    material = await service.complete_upload(material_id, payload.checksum)
    return MaterialResponse.model_validate(material)


@router.delete("/upload/{material_id}/cancel")
async def cancel_upload(
    material_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_material_permission(material_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = UploadService(db)
    await service.cancel_upload(material_id)
    return {"status": "cancelled"}
