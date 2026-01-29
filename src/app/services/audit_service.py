from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...app.models.audit_log import AuditAction, AuditLog, ResourceType

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log_event(
        self,
        action: AuditAction,
        resource_type: ResourceType,
        resource_id: str,
        success: bool,
        correlation_id: str,
        ip_address: str,
        user_agent: str | None = None,
        user_id: Optional[uuid.UUID] = None,
        details: Optional[dict] = None,
    ) -> None:
        try:
            audit_entry = AuditLog(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                success=success,
                details=details or {},
                correlation_id=correlation_id,
            )

            self._db.add(audit_entry)
            await self._db.flush()

        except Exception as exc:
            logger.error(f"Failed to log audit event: {exc}", exc_info=True)

    async def log_authentication(
        self,
        action: AuditAction,
        user_id: Optional[uuid.UUID],
        success: bool,
        ip_address: str,
        user_agent: str | None,
        correlation_id: str,
        details: Optional[dict] = None,
    ) -> None:
        await self.log_event(
            action=action,
            resource_type=ResourceType.USER,
            resource_id=str(user_id) if user_id else "anonymous",
            success=success,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            details=details,
        )

    async def log_permission_change(
        self,
        user_id: uuid.UUID,
        resource_type: ResourceType,
        resource_id: str,
        old_permission: str,
        new_permission: str,
        ip_address: str,
        user_agent: str | None,
        correlation_id: str,
    ) -> None:
        await self.log_event(
            action=AuditAction.ROLE_CHANGE,
            resource_type=resource_type,
            resource_id=resource_id,
            success=True,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            details={
                "old_permission": old_permission,
                "new_permission": new_permission,
            },
        )

    async def log_data_access(
        self,
        user_id: uuid.UUID,
        action: AuditAction,
        resource_type: ResourceType,
        resource_id: str,
        ip_address: str,
        user_agent: str | None,
        correlation_id: str,
        details: Optional[dict] = None,
    ) -> None:
        await self.log_event(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            success=True,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            details=details,
        )

    async def log_permission_denied(
        self,
        user_id: Optional[uuid.UUID],
        action: str,
        resource_type: ResourceType,
        resource_id: str,
        required_permission: str,
        ip_address: str,
        user_agent: str | None,
        correlation_id: str,
    ) -> None:
        await self.log_event(
            action=AuditAction.PERMISSION_DENIED,
            resource_type=resource_type,
            resource_id=resource_id,
            success=False,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            details={
                "attempted_action": action,
                "required_permission": required_permission,
            },
        )


async def log_audit_background(
    db_session_maker,
    action: AuditAction,
    resource_type: ResourceType,
    resource_id: str,
    success: bool,
    correlation_id: str,
    ip_address: str,
    user_agent: str | None = None,
    user_id: Optional[uuid.UUID] = None,
    details: Optional[dict] = None,
) -> None:
    try:
        async with db_session_maker() as session:
            service = AuditService(session)
            await service.log_event(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                success=success,
                correlation_id=correlation_id,
                ip_address=ip_address,
                user_agent=user_agent,
                user_id=user_id,
                details=details,
            )
            await session.commit()
    except Exception as exc:
        logger.error(f"Background audit logging failed: {exc}", exc_info=True)
