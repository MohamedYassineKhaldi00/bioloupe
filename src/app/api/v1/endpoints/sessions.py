from __future__ import annotations

from typing import Annotated, Tuple
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...app.db.base import get_db
from ...app.models.session import Session, SessionPermission
from ...app.api.dependencies.permissions import (
    require_session_permission,
    get_session_with_permission
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    session: Annotated[Session, Depends(
        lambda sid, user, svc, cache: require_session_permission(
            sid,
            [SessionPermission.read, SessionPermission.write, SessionPermission.admin],
            user, svc, cache
        )
    )],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    return {
        "session_id": session_id,
        "message": "Session retrieved successfully"
    }


@router.get("/{session_id}/details")
async def get_session_details(
    session_id: str,
    session_data: Annotated[
        Tuple[Session, SessionPermission],
        Depends(get_session_with_permission)
    ],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    _, permission = session_data

    response = {
        "session_id": session_id,
        "permission": permission.value,
        "basic_info": {}
    }

    if permission in [SessionPermission.write, SessionPermission.admin]:
        response["edit_capabilities"] = True

    if permission == SessionPermission.admin:
        response["admin_capabilities"] = True

    return response


@router.post("/{session_id}/materials")
async def add_material(
    session_id: str,
    session: Annotated[Session, Depends(
        lambda sid, user, svc, cache: require_session_permission(
            sid,
            [SessionPermission.write, SessionPermission.admin],
            user, svc, cache
        )
    )],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    return {
        "session_id": session_id,
        "message": "Material added successfully"
    }


@router.delete("/{session_id}/materials/{material_id}")
async def delete_material(
    session_id: str,
    material_id: str,
    session: Annotated[Session, Depends(
        lambda sid, user, svc, cache: require_session_permission(
            sid,
            [SessionPermission.write, SessionPermission.admin],
            user, svc, cache
        )
    )],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    return {
        "session_id": session_id,
        "material_id": material_id,
        "message": "Material deleted successfully"
    }


@router.post("/{session_id}/participants")
async def add_participant(
    session_id: str,
    session: Annotated[Session, Depends(
        lambda sid, user, svc, cache: require_session_permission(
            sid,
            [SessionPermission.admin],
            user, svc, cache
        )
    )],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    return {
        "session_id": session_id,
        "message": "Participant added successfully"
    }


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    session: Annotated[Session, Depends(
        lambda sid, user, svc, cache: require_session_permission(
            sid,
            [SessionPermission.admin],
            user, svc, cache
        )
    )],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    return {
        "session_id": session_id,
        "message": "Session deleted successfully"
    }
