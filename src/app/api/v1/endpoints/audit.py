from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....app.api.dependencies.auth import get_current_active_user
from ....app.db.base import get_db
from ....app.models.audit_log import AuditLog
from ....app.models.user import User
from ....app.schemas.audit_schemas import (
    AuditExportRequest,
    AuditLogListResponse,
    AuditLogQueryParams,
    AuditLogResponse,
)

router = APIRouter()


async def verify_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def query_audit_logs(
    params: AuditLogQueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(verify_admin_user),
) -> AuditLogListResponse:
    query = select(AuditLog)

    if params.start_date:
        query = query.where(AuditLog.timestamp >= params.start_date)

    if params.end_date:
        query = query.where(AuditLog.timestamp <= params.end_date)

    if params.user_id:
        query = query.where(AuditLog.user_id == params.user_id)

    if params.action:
        query = query.where(AuditLog.action == params.action)

    if params.resource_type:
        query = query.where(AuditLog.resource_type == params.resource_type)

    if params.resource_id:
        query = query.where(AuditLog.resource_id == params.resource_id)

    if params.success is not None:
        query = query.where(AuditLog.success == params.success)

    if params.ip_address:
        query = query.where(AuditLog.ip_address == params.ip_address)

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(AuditLog.timestamp))
    query = query.limit(params.limit).offset(params.offset)

    result = await db.execute(query)
    logs = result.scalars().all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get("/audit-logs/user/{user_id}", response_model=AuditLogListResponse)
async def get_user_audit_trail(
    user_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(verify_admin_user),
) -> AuditLogListResponse:
    query = select(AuditLog).where(AuditLog.user_id == user_id)

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(AuditLog.timestamp))
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    logs = result.scalars().all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/audit-logs/resource/{resource_type}/{resource_id}",
    response_model=AuditLogListResponse,
)
async def get_resource_audit_trail(
    resource_type: str,
    resource_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(verify_admin_user),
) -> AuditLogListResponse:
    query = select(AuditLog).where(
        AuditLog.resource_type == resource_type,
        AuditLog.resource_id == resource_id,
    )

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(AuditLog.timestamp))
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    logs = result.scalars().all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/audit-logs/export")
async def export_audit_logs(
    export_request: AuditExportRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(verify_admin_user),
) -> StreamingResponse:
    query = select(AuditLog)

    if export_request.start_date:
        query = query.where(AuditLog.timestamp >= export_request.start_date)

    if export_request.end_date:
        query = query.where(AuditLog.timestamp <= export_request.end_date)

    if export_request.user_id:
        query = query.where(AuditLog.user_id == export_request.user_id)

    if export_request.action:
        query = query.where(AuditLog.action == export_request.action)

    if export_request.resource_type:
        query = query.where(
            AuditLog.resource_type == export_request.resource_type
        )

    query = query.order_by(desc(AuditLog.timestamp))

    result = await db.execute(query)
    logs = result.scalars().all()

    if export_request.format == "csv":
        return _export_csv(logs, export_request.include_details)

    return _export_json(logs, export_request.include_details)


def _export_csv(logs: list[AuditLog], include_details: bool) -> StreamingResponse:
    output = io.StringIO()

    fieldnames = [
        "id",
        "timestamp",
        "user_id",
        "ip_address",
        "user_agent",
        "action",
        "resource_type",
        "resource_id",
        "success",
        "correlation_id",
    ]

    if include_details:
        fieldnames.append("details")

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for log in logs:
        row = {
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat(),
            "user_id": str(log.user_id) if log.user_id else "",
            "ip_address": log.ip_address,
            "user_agent": log.user_agent or "",
            "action": log.action.value,
            "resource_type": log.resource_type.value,
            "resource_id": log.resource_id,
            "success": log.success,
            "correlation_id": log.correlation_id,
        }

        if include_details:
            row["details"] = json.dumps(log.details) if log.details else ""

        writer.writerow(row)

    output.seek(0)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"audit_logs_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _export_json(logs: list[AuditLog], include_details: bool) -> StreamingResponse:
    data = []

    for log in logs:
        log_dict = {
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat(),
            "user_id": str(log.user_id) if log.user_id else None,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "action": log.action.value,
            "resource_type": log.resource_type.value,
            "resource_id": log.resource_id,
            "success": log.success,
            "correlation_id": log.correlation_id,
        }

        if include_details:
            log_dict["details"] = log.details

        data.append(log_dict)

    json_output = json.dumps(data, indent=2)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"audit_logs_{timestamp}.json"

    return StreamingResponse(
        iter([json_output]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
